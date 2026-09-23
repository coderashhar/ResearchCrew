import type { Critique, Draft, ResearchEvent, SavedRun, SourceSummary, SearchQuery } from "./types";

export type Step = "idle" | "plan" | "research" | "write" | "critique" | "done";

export type RunState = {
  runId: string | null;
  topic: string;
  step: Step;
  queries: SearchQuery[];
  sources: SourceSummary[];
  drafts: Draft[];
  report: string | null;
  score: number | null;
  elapsed: number | null;
  /** Rewrites so far: 0 while the first draft is being written. */
  revision: number;
  researchRound: number;
  error: string | null;
};

export const initialState: RunState = {
  runId: null,
  topic: "",
  step: "idle",
  queries: [],
  sources: [],
  drafts: [],
  report: null,
  score: null,
  elapsed: null,
  revision: 0,
  researchRound: 0,
  error: null,
};

export type Action =
  | { type: "start"; topic: string }
  | { type: "event"; event: ResearchEvent }
  | { type: "failed"; message: string }
  | { type: "load"; run: SavedRun };

export function runReducer(state: RunState, action: Action): RunState {
  switch (action.type) {
    case "start":
      return { ...initialState, topic: action.topic, step: "plan" };

    case "failed":
      return { ...state, step: "done", error: action.message };

    case "load":
      return loadSaved(action.run);

    case "event":
      return applyEvent(state, action.event);
  }
}

function applyEvent(state: RunState, event: ResearchEvent): RunState {
  switch (event.name) {
    case "run":
      return { ...state, runId: event.data.id };

    case "plan":
      return { ...state, step: "research", queries: event.data.queries };

    case "sources": {
      // Ids are unique and stable, so a replayed event cannot duplicate a source.
      const known = new Set(state.sources.map((s) => s.id));
      const added = event.data.added.filter((s) => !known.has(s.id));
      return {
        ...state,
        step: "write",
        researchRound: event.data.round,
        sources: [...state.sources, ...added],
      };
    }

    case "draft":
      return {
        ...state,
        step: "critique",
        revision: event.data.version - 1,
        drafts: upsertDraft(state.drafts, {
          version: event.data.version,
          report: event.data.report,
          critique: null,
        }),
      };

    case "critique":
      return {
        ...state,
        drafts: withCritique(state.drafts, event.data.version, event.data.critique),
      };

    case "final":
      return {
        ...state,
        step: "done",
        report: event.data.report,
        score: event.data.score,
        sources: event.data.sources,
        drafts: event.data.drafts,
        elapsed: event.data.elapsed_s,
      };

    case "error":
      return { ...state, step: "done", error: event.data.message };
  }
}

function upsertDraft(drafts: Draft[], draft: Draft): Draft[] {
  const rest = drafts.filter((d) => d.version !== draft.version);
  return [...rest, draft].sort((a, b) => a.version - b.version);
}

function withCritique(drafts: Draft[], version: number, critique: Critique): Draft[] {
  return drafts.map((d) => (d.version === version ? { ...d, critique } : d));
}

function loadSaved(run: SavedRun): RunState {
  return {
    ...initialState,
    runId: run.id,
    topic: run.topic,
    step: "done",
    queries: run.queries,
    sources: run.sources,
    drafts: run.drafts,
    report: run.final_report,
    score: run.final_score,
    elapsed: run.elapsed_s,
    revision: Math.max(run.drafts.length - 1, 0),
    error: run.error,
  };
}

/** Scores in draft order, for the "v1 5 → v2 8" history. */
export function scoreHistory(drafts: Draft[]): { version: number; score: number }[] {
  return drafts
    .filter((d) => d.critique)
    .map((d) => ({ version: d.version, score: d.critique!.overall }));
}
