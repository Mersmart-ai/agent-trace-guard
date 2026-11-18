/**
 * fbs-dsh-monitor: observe-only dsh plugin.
 *
 * Subscribes to the durable session event stream and appends every event as
 * JSONL. It does not modify agent behavior.
 */
import fs from "node:fs";
import path from "node:path";

export const name = "fbs-dsh-monitor";
export const inject = [];

let outPath = "";

function ensureParent(file) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
}

function safeJson(value) {
  try {
    return JSON.stringify(value);
  } catch (error) {
    return JSON.stringify({ error: String(error) });
  }
}

export function apply(ctx, config = {}) {
  outPath = config.out || path.resolve("dsh-events.jsonl");
  ensureParent(outPath);
  console.error(`[fbs-monitor] loaded; out=${outPath}`);

  ctx.on("session/event", (session, event) => {
    const row = {
      ts: new Date().toISOString(),
      session: session?.id ?? null,
      event,
    };
    try {
      fs.appendFileSync(outPath, safeJson(row) + "\n");
    } catch (error) {
      console.error("[fbs-monitor] write failed", error);
    }
  });
}
