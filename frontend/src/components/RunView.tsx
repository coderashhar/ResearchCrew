"use client";

import { LiveLog } from "@/components/LiveLog";
import { PipelineTracker } from "@/components/PipelineTracker";
import { ResultView } from "@/components/ResultView";
import { TopicForm } from "@/components/TopicForm";
import { useResearchRun } from "@/hooks/useResearchRun";
import type { SavedRun } from "@/lib/types";

export function RunView({ saved }: { saved?: SavedRun }) {
  const { state, running, start } = useResearchRun(saved);

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-10">
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold">ResearchCrew</h1>
        <p className="text-muted">
          Four agents plan, read, write and check a cited research report.
        </p>
      </header>

      <TopicForm running={running} onSubmit={start} />

      {state.topic && (
        <section className="space-y-4">
          <h2 className="text-lg text-muted">{state.topic}</h2>
          <PipelineTracker step={state.step} revision={state.revision} />
          {/* Kept after the run: it is the record of what was searched and
              read, not just a progress indicator. */}
          <details open={state.step !== "done"}>
            <summary className="cursor-pointer text-sm text-faint">Run log</summary>
            <div className="mt-2">
              <LiveLog state={state} />
            </div>
          </details>
        </section>
      )}

      {state.error && (
        <p role="alert" className="card border-rose/40 p-4 text-rose">
          {state.error}
        </p>
      )}

      <ResultView state={state} />
    </main>
  );
}
