import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { LiveLog, logLines } from "./LiveLog";
import { initialState, type RunState } from "@/lib/runReducer";
import type { Critique } from "@/lib/types";

const critique = (overall: number): Critique => ({
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
});

const state: RunState = {
  ...initialState,
  topic: "T",
  queries: [
    { query: "how mRNA works", topic: "general", days: null },
    { query: "mRNA approvals", topic: "news", days: 30 },
  ],
  sources: [{ id: 1, title: "A paper", domain: "nature.com", url: "https://nature.com/p" }],
  drafts: [{ version: 1, report: "three words here", critique: critique(5) }],
};

describe("LiveLog", () => {
  it("shows queries, sources, drafts and scores", () => {
    expect(logLines(state).map((l) => l.text)).toEqual([
      "Search: how mRNA works",
      "News: mRNA approvals",
      "[1] nature.com — A paper",
      "Draft v1, 3 words",
      "Checked v1: 5/10",
    ]);
  });

  it("flags a failing score", () => {
    const [low] = logLines(state).slice(-1);
    expect(low.tone).toBe("amber");
    const passing = logLines({
      ...state,
      drafts: [{ ...state.drafts[0], critique: critique(8) }],
    });
    expect(passing.at(-1)?.tone).toBeUndefined();
  });

  it("renders nothing before the first event", () => {
    const { container } = render(<LiveLog state={initialState} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders one line per entry", () => {
    render(<LiveLog state={state} />);
    expect(screen.getAllByRole("listitem")).toHaveLength(5);
  });
});
