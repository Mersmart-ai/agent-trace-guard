/**
 * fbs-dsh-intervene: turn-stopping guard for the first-bad-step experiments.
 *
 * shadow — log what would happen, never steer
 * guard  — steer the agent when it tries to finish without verification
 *
 * The guard only looks at the process (was there a test after the last write?),
 * not at the final answer. State is per-agent and in-memory; a resumed session
 * starts fresh.
 */
import fs from "node:fs";
import path from "node:path";
import { randomUUID } from "node:crypto";

export const name = "fbs-dsh-intervene";
export const inject = [];

const DEFAULTS = {
  mode: "shadow",
  out: "dsh-intervene.jsonl",
  maxSteers: 1,
};

const LOOKUP_CMDS = new Set([
  "get-command", "get-childitem", "get-help", "get-item", "where", "which",
]);
const PS_WRITE_CMDS = new Set([
  "set-content", "add-content", "clear-content", "out-file", "tee-object",
  "new-item", "remove-item", "copy-item", "move-item", "rename-item",
  "set-item", "set-itemproperty", "new-itemproperty", "remove-itemproperty",
]);
const PYTEST_INFO = /pytest(?:\.exe)?\s+(?:--version|--help|-h|--collect-only)\b/;
const PYTEST_ARG = /(?<![\w-])pytest(?:\.exe)?\s+(?:-{1,2}\w|tests?\b)/;
const PS_REDIRECT = /(?<![\d&])>{1,2}(?!&)/;
const FAILED_LINE = /^(?:FAILED|ERROR)\s+(\S+)/;
const PASSED_COUNT = /\b\d+ passed\b/;
const FAILED_COUNT = /\b\d+ (?:failed|errors?)\b/;

function segments(command) {
  return String(command || "")
    .split(/\|\||&&|[|;]/)
    .map((part) => part.trim())
    .filter(Boolean);
}

function isTestCommand(command) {
  for (const seg of segments(command)) {
    const words = seg.split(/\s+/);
    if (words.length && LOOKUP_CMDS.has(words[0].toLowerCase())) continue;
    if (PYTEST_INFO.test(seg)) continue;
    if (seg.includes("-m pytest") || PYTEST_ARG.test(seg)) return true;
  }
  return false;
}

function isWriteCall(exec) {
  if (exec.name === "write" || exec.name === "edit" || exec.name === "write_file") {
    return true;
  }
  if (exec.name !== "pwsh") return false;
  const command = String((exec.arguments || {}).command || "");
  if (PS_REDIRECT.test(command)) return true;
  for (const seg of segments(command)) {
    const first = seg.split(/\s+/)[0]?.toLowerCase();
    if (first && PS_WRITE_CMDS.has(first)) return true;
  }
  return false;
}

function textOf(result) {
  return (result?.content || [])
    .filter((part) => part && typeof part.text === "string")
    .map((part) => part.text)
    .join("\n");
}

function parseTestState(text) {
  if (!text) return null;
  const failed = new Set();
  for (const line of text.split(/\r?\n/)) {
    const match = line.trim().match(FAILED_LINE);
    if (match) failed.add(match[1].split(" - ")[0].split("::").pop());
  }
  if (failed.size) return [...failed].sort();
  if (PASSED_COUNT.test(text) && !FAILED_COUNT.test(text)) return [];
  if (/No module named pytest|ModuleNotFoundError|not recognized as/i.test(text)) {
    return ["<pytest_no_case>"];
  }
  return null;
}

const states = new WeakMap();

function stateOf(agent) {
  let state = states.get(agent);
  if (!state) {
    state = {
      steps: 0,
      lastWrite: 0,
      lastTest: 0,
      lastState: null,
      hasTest: false,
      steers: 0,
    };
    states.set(agent, state);
  }
  return state;
}

function remember(agent, exec, result) {
  const state = stateOf(agent);
  state.steps += 1;

  if (isWriteCall(exec)) {
    state.lastWrite = state.steps;
    return;
  }

  const isTest = exec.name === "run_tests"
    || (exec.name === "pwsh" && isTestCommand((exec.arguments || {}).command));
  if (!isTest) return;

  state.hasTest = true;
  state.lastTest = state.steps;
  const parsed = parseTestState(textOf(result));
  if (parsed !== null) state.lastState = parsed;
}

function problems(state) {
  const rules = [];
  // 只有确实写过文件才要求验证；纯问答/只读任务不拦。
  if (!state.hasTest && state.lastWrite > 0) rules.push("no_test");
  if (state.lastWrite > state.lastTest) rules.push("write_after_test");
  if (state.lastState && state.lastState.length) {
    rules.push(state.lastState[0] === "<pytest_no_case>" ? "test_not_runnable" : "last_test_red");
  }
  return rules;
}

function steerText(rules, state) {
  return [
    "You are about to finish, but this session has no passing test result after the last edit.",
    "",
    `Observed: ${rules.join(", ")}`,
    `Steps since last test: ${state.steps - state.lastTest}`,
    "",
    "Before finishing: run the project's test suite (`python -m pytest -q` or the configured judge).",
    "If it cannot run, report the exact blocking error instead of claiming success.",
  ].join("\n");
}

function message(text, summary) {
  return {
    role: "user",
    id: randomUUID(),
    content: [{ type: "text", text }],
    source: { kind: "fbs-intervene", form: "notice", summary },
  };
}

function appendLog(out, row) {
  try {
    fs.appendFileSync(out, JSON.stringify({ ts: new Date().toISOString(), ...row }) + "\n");
  } catch (error) {
    console.error(`[fbs-intervene] log failed: ${error}`);
  }
}

export function apply(ctx, config = {}) {
  const cfg = { ...DEFAULTS, ...config };
  if (cfg.mode !== "shadow" && cfg.mode !== "guard") {
    throw new Error(`fbs-intervene: invalid mode ${cfg.mode}`);
  }
  const out = path.resolve(cfg.out);
  console.error(`[fbs-intervene] loaded mode=${cfg.mode}; out=${out}`);

  ctx.on("tools/post-execute", async (exec, result, next) => {
    try {
      if (exec.agent) remember(exec.agent, exec, result);
    } catch (error) {
      console.error(`[fbs-intervene] observe failed: ${error}`);
    }
    return next();
  });

  // 新用户消息开始新一轮，清掉上一轮的状态；我们自己的 steer 不算用户消息。
  ctx.on("agent/pre-step", ({ agent, messages }, next) => {
    if (messages.some((item) => item.source?.kind === "user")) states.delete(agent);
    return next();
  });

  ctx.on("agent/turn-stopping", ({ agent, turn }) => {
    const state = stateOf(agent);
    const rules = problems(state);
    if (!rules.length) return;

    const row = {
      mode: cfg.mode,
      agent: agent.id,
      turn,
      step: state.steps,
      rules,
      last_test_state: state.lastState,
    };

    if (cfg.mode === "shadow") {
      appendLog(out, { ...row, action: "shadow" });
      return;
    }
    if (state.steers >= cfg.maxSteers) {
      appendLog(out, { ...row, action: "skip_max_steers" });
      return;
    }

    state.steers += 1;
    appendLog(out, { ...row, action: "steer" });
    try {
      agent.steer(message(steerText(rules, state), rules.join(",")));
    } catch (error) {
      console.error(`[fbs-intervene] steer failed: ${error}`);
    }
  });
}
