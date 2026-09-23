"use client";

import { LiveLog } from "@/components/LiveLog";
import { PipelineTracker } from "@/components/PipelineTracker";
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
          <PipelineTracker step={state.step} revision={state.revision} />
          <LiveLog state={state} />
        </section>
      )}

      {state.error && (
        <p role="alert" className="card border-rose/40 p-4 text-rose">
          {state.error}
        </p>
      )}

      {state.report && (
        <article className="card whitespace-pre-wrap p-6 leading-relaxed">{state.report}</article>
      )}
    </main>
  );
}
