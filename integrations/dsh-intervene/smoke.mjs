import { apply } from "./index.js";

function fake(mode, maxSteers = 1) {
  const handlers = {};
  const ctx = { on: (name, fn) => { handlers[name] = fn; } };
  apply(ctx, { mode, out: "data/dsh/intervene_test.jsonl", maxSteers });
  const agent = {
    id: `agent-${mode}`,
    steers: [],
    steer(message) { this.steers.push(message); },
  };
  const next = async () => ({ kind: "ok" });
  const write = (name, args = {}, text = "ok") => handlers["tools/post-execute"](
    { agent, name, arguments: args },
    { content: [{ type: "text", text }] },
    next,
  );
  const test = (text) => handlers["tools/post-execute"](
    { agent, name: "pwsh", arguments: { command: "python -m pytest -q" } },
    { content: [{ type: "text", text }] },
    next,
  );
  const user = () => handlers["agent/pre-step"](
    { agent, messages: [{ source: { kind: "user" } }] },
    next,
  );
  const stop = () => handlers["agent/turn-stopping"]({ agent, turn: 1 });
  return { agent, write, test, user, stop };
}

const cases = [];

{
  const t = fake("guard");
  await t.user();
  await t.write("edit");
  t.stop();
  cases.push(["write then finish", t.agent.steers.length, t.agent.steers[0]?.content?.[0]?.text.split("\n")[3]]);
}

{
  const t = fake("guard");
  await t.user();
  await t.write("edit");
  await t.test("153 passed in 0.2s");
  t.stop();
  cases.push(["write then green test", t.agent.steers.length]);
}

{
  const t = fake("guard");
  await t.user();
  await t.write("edit");
  await t.test("FAILED tests/test_a.py::test_x - AssertionError\n1 failed, 2 passed");
  t.stop();
  cases.push(["write then red test", t.agent.steers.length, t.agent.steers[0]?.content?.[0]?.text.split("\n")[3]]);
}

{
  const t = fake("guard");
  await t.user();
  await t.test("No module named pytest");
  t.stop();
  cases.push(["test cannot run", t.agent.steers.length, t.agent.steers[0]?.content?.[0]?.text.split("\n")[3]]);
}

{
  const t = fake("guard");
  await t.user();
  await t.write("edit");
  t.stop();
  t.stop();
  cases.push(["max steers", t.agent.steers.length]);
}

{
  const t = fake("guard");
  await t.user();
  await t.write("edit", { file_path: "pytest.ini" });
  await t.test("154 passed");
  t.stop();
  cases.push([
    "forbidden config write",
    t.agent.steers.length,
    t.agent.steers[0]?.content?.[0]?.text.includes("pytest.ini"),
  ]);
}

{
  const t = fake("guard", 2);
  await t.user();
  await t.write("edit");
  t.stop();
  t.stop();
  cases.push(["two steers allowed", t.agent.steers.length]);
}

{
  const t = fake("shadow");
  await t.user();
  await t.write("edit");
  t.stop();
  cases.push(["shadow does not steer", t.agent.steers.length]);
}

for (const row of cases) console.log(...row);
