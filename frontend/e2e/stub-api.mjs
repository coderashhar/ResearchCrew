// A stand-in for the Python service: the browser tests exercise the real
// Next.js routing and streaming, without Tavily, Mistral or Postgres.
import { createServer } from "node:http";
import { readFileSync } from "node:fs";

const fixtures = JSON.parse(readFileSync(new URL("./fixtures.json", import.meta.url), "utf8"));
const { runId, topic, report, queries, sources, drafts } = fixtures;
const PORT = Number(process.env.STUB_PORT ?? 3101);

const frame = (name, data) => `event: ${name}\ndata: ${JSON.stringify(data)}\n\n`;

const stream = [
  frame("run", { id: runId }),
  frame("plan", { queries }),
  frame("sources", { added: sources, round: 1 }),
  frame("draft", { version: 1, report: drafts[0].report }),
  frame("critique", { version: 1, critique: drafts[0].critique }),
  frame("draft", { version: 2, report: drafts[1].report }),
  frame("critique", { version: 2, critique: drafts[1].critique }),
  frame("final", { report, score: 8, sources, drafts, elapsed_s: 42.5 }),
];

const savedRun = {
  id: runId,
  topic,
  created_at: "2026-01-01T00:00:00Z",
  status: "done",
  final_report: report,
  final_score: 8,
  drafts,
  sources,
  queries,
  elapsed_s: 42.5,
  error: null,
};

createServer((req, res) => {
  const url = new URL(req.url, "http://localhost");

  if (url.pathname === "/api/health") {
    return json(res, 200, { status: "ok" });
  }
  if (url.pathname === "/api/research" && req.method === "POST") {
    res.writeHead(200, { "content-type": "text/event-stream", "cache-control": "no-cache" });
    let i = 0;
    const tick = setInterval(() => {
      res.write(stream[i++]);
      if (i === stream.length) {
        clearInterval(tick);
        res.end();
      }
    }, 30); // arrive over time, like a real run
    return;
  }
  if (url.pathname === `/api/runs/${runId}`) {
    return json(res, 200, savedRun);
  }
  return json(res, 404, { detail: "No such run" });
}).listen(PORT, () => console.log(`stub api on ${PORT}`));

function json(res, status, body) {
  res.writeHead(status, { "content-type": "application/json" });
  res.end(JSON.stringify(body));
}
