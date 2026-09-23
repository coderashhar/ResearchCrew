import type { UnsupportedClaim } from "@/lib/types";

/**
 * Claims the critic could not match to their cited source. Deliberately
 * static: a warning should not feel playful.
 */
export function UnsupportedClaims({ claims }: { claims: UnsupportedClaim[] }) {
  if (claims.length === 0) return null;

  return (
    <section className="card space-y-3 p-4" aria-label="Unsupported claims">
      <h3 className="text-sm font-medium text-rose">
        {claims.length === 1 ? "1 claim the sources do not support" : `${claims.length} claims the sources do not support`}
      </h3>
      <ul className="space-y-3">
        {claims.map((claim, i) => (
          <li key={i} className="border-l-2 border-rose/50 pl-3 text-sm">
            <p className="text-fg">{claim.claim}</p>
            <p className="text-muted">
              {claim.source_id === null ? "Uncited" : `Cites [${claim.source_id}]`} — {claim.reason}
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
}
