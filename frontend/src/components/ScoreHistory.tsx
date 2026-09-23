import { scoreHistory } from "@/lib/runReducer";
import type { Draft } from "@/lib/types";

export function scoreColor(score: number): string {
  if (score >= 8) return "text-emerald border-emerald/40";
  if (score >= 6) return "text-amber border-amber/40";
  return "text-rose border-rose/40";
}

/** The revision story: a weak first draft and what it became. */
export function ScoreHistory({ drafts }: { drafts: Draft[] }) {
  const history = scoreHistory(drafts);
  if (history.length === 0) return null;

  return (
    <div className="flex items-center gap-2" aria-label="Score history">
      {history.map(({ version, score }, i) => (
        <div key={version} className="flex items-center gap-2">
          {i > 0 && <span className="text-faint">→</span>}
          <span
            data-testid={`score-v${version}`}
            className={`enter rounded-full border px-3 py-1 text-sm ${scoreColor(score)}`}
          >
            v{version} · {score}/10
          </span>
        </div>
      ))}
    </div>
  );
}
