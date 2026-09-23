import { describe, expect, it } from "vitest";

import { initialState, runReducer, scoreHistory, type RunState } from "./runReducer";
import type { Critique, ResearchEvent, SavedRun } from "./types";

const critique = (overall: number, extra: Partial<Critique> = {}): Critique => ({
  accuracy: overall,
  coverage: overall,
  citation_quality: overall,
  clarity: overall,
  recency: overall,
  overall,
  strengths: [],
  gaps: [],
  unsupported_claims: [],
  needs_more_research: false,
  followup_queries: [],
  ...extra,
});

const source = (id: number) => ({
  id,
  title: `T${id}`,
  domain: `d${id}.com`,
  url: `https://d${id}.com/p`,
});

function play(events: ResearchEvent[], from: RunState = initialState): RunState {
  return events.reduce((state, event) => runReducer(state, { type: "event", event }), from);
}

const FULL_RUN: ResearchEvent[] = [
  { name: "run", data: { id: "run-1" } },
  { name: "plan", data: { queries: [{ query: "q", topic: "general", days: null }] } },
  { name: "sources", data: { added: [source(1), source(2)], round: 1 } },
  { name: "draft", data: { version: 1, report: "v1 [1]" } },
  { name: "critique", data: { version: 1, critique: critique(5) } },
  { name: "draft", data: { version: 2, report: "v2 [1] [2]" } },
  { name: "critique", data: { version: 2, critique: critique(8) } },
  {
    name: "final",
    data: {
      report: "v2 [1] [2]\n\n## Sources",
      score: 8,
      sources: [source(1), source(2)],
      drafts: [
        { version: 1, report: "v1 [1]", critique: critique(5) },
        { version: 2, report: "v2 [1] [2]", critique: critique(8) },
      ],
      elapsed_s: 42.5,
    },
  },
];

describe("runReducer", () => {
  it("starts a run and clears the previous one", () => {
    const state = runReducer(play(FULL_RUN), { type: "start", topic: "next" });
    expect(state).toEqual({ ...initialState, topic: "next", step: "plan" });
  });

  it("walks a full run to done", () => {
    const state = play(FULL_RUN);
    expect(state.step).toBe("done");
    expect(state.runId).toBe("run-1");
    expect(state.report).toContain("v2 [1] [2]");
    expect(state.score).toBe(8);
    expect(state.elapsed).toBe(42.5);
    expect(state.drafts).toHaveLength(2);
    expect(state.sources.map((s) => s.id)).toEqual([1, 2]);
  });

  it("tracks the step each event implies", () => {
    const steps = FULL_RUN.map((event, i) => play(FULL_RUN.slice(0, i + 1)).step);
    expect(steps).toEqual([
      "idle",
      "research",
      "write",
      "critique",
      "critique",
      "critique",
      "critique",
      "done",
    ]);
  });

  it("counts rewrites, not drafts", () => {
    expect(play(FULL_RUN.slice(0, 4)).revision).toBe(0);
    expect(play(FULL_RUN.slice(0, 6)).revision).toBe(1);
  });

  it("attaches each critique to its own draft", () => {
    const state = play(FULL_RUN.slice(0, 7));
    expect(state.drafts.map((d) => d.critique?.overall)).toEqual([5, 8]);
  });

  it("ignores sources it already has", () => {
    const state = play([
      ...FULL_RUN.slice(0, 3),
      { name: "sources", data: { added: [source(2), source(3)], round: 2 } },
    ]);
    expect(state.sources.map((s) => s.id)).toEqual([1, 2, 3]);
    expect(state.researchRound).toBe(2);
  });

  it("records an error event as a finished, failed run", () => {
    const state = play([...FULL_RUN.slice(0, 3), { name: "error", data: { message: "boom" } }]);
    expect(state).toMatchObject({ step: "done", error: "boom", report: null });
  });

  it("records a transport failure", () => {
    const state = runReducer(initialState, { type: "failed", message: "connection lost" });
    expect(state).toMatchObject({ step: "done", error: "connection lost" });
  });

  it("loads a saved run", () => {
    const saved: SavedRun = {
      id: "saved-1",
      topic: "mRNA",
      created_at: "2026-01-01T00:00:00Z",
      status: "done",
      final_report: "report [1]",
      final_score: 9,
      drafts: [{ version: 1, report: "report [1]", critique: critique(9) }],
      sources: [source(1)],
      queries: [{ query: "q", topic: "general", days: null }],
      elapsed_s: 30,
      error: null,
    };
    expect(runReducer(initialState, { type: "load", run: saved })).toMatchObject({
      runId: "saved-1",
      topic: "mRNA",
      step: "done",
      report: "report [1]",
      score: 9,
      revision: 0,
    });
  });
});

describe("scoreHistory", () => {
  it("lists judged drafts in order", () => {
    expect(scoreHistory(play(FULL_RUN).drafts)).toEqual([
      { version: 1, score: 5 },
      { version: 2, score: 8 },
    ]);
  });

  it("skips a draft that has not been checked yet", () => {
    expect(scoreHistory(play(FULL_RUN.slice(0, 4)).drafts)).toEqual([]);
  });
});
