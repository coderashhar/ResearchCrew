import type { SourceSummary } from "@/lib/types";

/** Ids that appear as [n] in the report. */
export function citedIds(report: string): Set<number> {
  const ids = new Set<number>();
  for (const match of report.matchAll(/\[(\d+(?:\s*,\s*\d+)*)\]/g)) {
    for (const part of match[1].split(",")) ids.add(Number(part.trim()));
  }
  return ids;
}

export function SourcesList({
  sources,
  report,
}: {
  sources: SourceSummary[];
  report: string;
}) {
  const cited = citedIds(report);
  const used = sources.filter((s) => cited.has(s.id));
  const unused = sources.filter((s) => !cited.has(s.id));

  return (
    <section className="card space-y-4 p-4" aria-label="Sources">
      <Group title="Cited in the report" sources={used} testid="cited" />
      {unused.length > 0 && (
        // Read but never cited: it shows how much was rejected.
        <Group title="Read but not cited" sources={unused} testid="uncited" muted />
      )}
    </section>
  );
}

function Group({
  title,
  sources,
  testid,
  muted = false,
}: {
  title: string;
  sources: SourceSummary[];
  testid: string;
  muted?: boolean;
}) {
  return (
    <div className="space-y-2">
      <h3 className="text-sm font-medium text-muted">{title}</h3>
      <ul data-testid={`sources-${testid}`} className="space-y-1 text-sm">
        {sources.map((source) => (
          <li key={source.id} className={muted ? "text-faint" : "text-fg"}>
            <span className="tabular-nums text-faint">[{source.id}]</span>{" "}
            <a
              href={source.url}
              target="_blank"
              rel="noreferrer noopener"
              className="underline underline-offset-2"
            >
              {source.title}
            </a>{" "}
            <span className="text-faint">· {source.domain}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
