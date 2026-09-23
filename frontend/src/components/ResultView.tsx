"use client";

import { Drafts } from "@/components/Drafts";
import { Report } from "@/components/Report";
import { RubricBars } from "@/components/RubricBars";
import { ScoreHistory } from "@/components/ScoreHistory";
import { SourcesList } from "@/components/SourcesList";
import { UnsupportedClaims } from "@/components/UnsupportedClaims";
import type { RunState } from "@/lib/runReducer";

export function markdownFilename(topic: string): string {
  const slug = topic.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 60);
  return `${slug || "research-report"}.md`;
}

export function ResultView({ state }: { state: RunState }) {
  if (!state.report) return null;

  const latest = state.drafts.at(-1)?.critique ?? null;

  return (
    <section className="space-y-6" aria-label="Result">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <ScoreHistory drafts={state.drafts} />
        <div className="flex items-center gap-3 text-sm text-faint">
          {state.elapsed !== null && <span>{state.elapsed}s</span>}
          <DownloadButton topic={state.topic} report={state.report} />
        </div>
      </div>

      <Report report={state.report} sources={state.sources} />

      {latest && (
        <div className="card space-y-4 p-4">
          <RubricBars critique={latest} />
          {latest.gaps.length > 0 && (
            <ul className="space-y-1 text-sm text-muted">
              {latest.gaps.map((gap, i) => (
                <li key={i}>— {gap}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {latest && <UnsupportedClaims claims={latest.unsupported_claims} />}

      <SourcesList sources={state.sources} report={state.report} />
      <Drafts drafts={state.drafts} />
    </section>
  );
}

function DownloadButton({ topic, report }: { topic: string; report: string }) {
  const href = `data:text/markdown;charset=utf-8,${encodeURIComponent(report)}`;
  return (
    <a
      href={href}
      download={markdownFilename(topic)}
      className="pressable rounded-xl border border-glass px-3 py-1.5 text-muted"
    >
      Download .md
    </a>
  );
}
