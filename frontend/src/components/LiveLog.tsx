import type { RunState } from "@/lib/runReducer";

type Line = { key: string; text: string; tone?: "muted" | "amber" };

export function logLines(state: RunState): Line[] {
  const lines: Line[] = state.queries.map((q, i) => ({
    key: `q${i}`,
    text: `${q.topic === "news" ? "News" : "Search"}: ${q.query}`,
  }));

  lines.push(
    ...state.sources.map((s) => ({
      key: `s${s.id}`,
      text: `[${s.id}] ${s.domain} — ${s.title}`,
      tone: "muted" as const,
    })),
  );

  for (const draft of state.drafts) {
    lines.push({
      key: `d${draft.version}`,
      text: `Draft v${draft.version}, ${draft.report.split(/\s+/).filter(Boolean).length} words`,
    });
    if (draft.critique) {
      lines.push({
        key: `c${draft.version}`,
        text: `Checked v${draft.version}: ${draft.critique.overall}/10`,
        tone: draft.critique.overall >= 7 ? undefined : "amber",
      });
    }
  }

  return lines;
}

export function LiveLog({ state }: { state: RunState }) {
  const lines = logLines(state);
  if (lines.length === 0) return null;

  return (
    <ul className="card space-y-1 p-4 font-mono text-sm" aria-label="Run log">
      {lines.map((line) => (
        <li
          key={line.key}
          className={`enter ${line.tone === "muted" ? "text-muted" : line.tone === "amber" ? "text-amber" : "text-fg"}`}
        >
          {line.text}
        </li>
      ))}
    </ul>
  );
}
