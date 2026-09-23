import { RubricBars } from "@/components/RubricBars";
import { scoreColor } from "@/components/ScoreHistory";
import type { Draft } from "@/lib/types";

/** Earlier drafts, so the critique can be checked against what it judged. */
export function Drafts({ drafts }: { drafts: Draft[] }) {
  const earlier = drafts.slice(0, -1);
  if (earlier.length === 0) return null;

  return (
    <section className="space-y-2" aria-label="Earlier drafts">
      {earlier.map((draft) => (
        <details key={draft.version} className="card p-4">
          <summary className="cursor-pointer text-sm text-muted">
            Draft v{draft.version}
            {draft.critique && (
              <span className={`ml-2 ${scoreColor(draft.critique.overall).split(" ")[0]}`}>
                {draft.critique.overall}/10
              </span>
            )}
          </summary>
          <div className="mt-3 space-y-3">
            {draft.critique && <RubricBars critique={draft.critique} />}
            {draft.critique?.gaps.length ? (
              <ul className="space-y-1 text-sm text-muted">
                {draft.critique.gaps.map((gap, i) => (
                  <li key={i}>— {gap}</li>
                ))}
              </ul>
            ) : null}
            <p className="whitespace-pre-wrap text-sm text-muted">{draft.report}</p>
          </div>
        </details>
      ))}
    </section>
  );
}
