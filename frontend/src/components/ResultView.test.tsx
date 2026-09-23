import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ResultView, markdownFilename } from "./ResultView";
import { initialState, type RunState } from "@/lib/runReducer";
import type { Critique, SourceSummary } from "@/lib/types";

const critique = (overall: number, extra: Partial<Critique> = {}): Critique => ({
  accuracy: 6,
  coverage: 7,
  citation_quality: 9,
  clarity: 8,
  recency: 5,
  overall,
  strengths: [],
  gaps: ["No dates on the trial results"],
  unsupported_claims: [],
  needs_more_research: false,
  followup_queries: [],
  ...extra,
});

const sources: SourceSummary[] = [
  { id: 1, title: "Cited paper", domain: "nature.com", url: "https://nature.com/a" },
  { id: 2, title: "Unused paper", domain: "who.int", url: "https://who.int/b" },
];

const state: RunState = {
  ...initialState,
  topic: "mRNA vaccines",
  step: "done",
  report: "A claim [1].",
  score: 8,
  elapsed: 42.5,
  sources,
  drafts: [
    { version: 1, report: "weak [1]", critique: critique(5) },
    { version: 2, report: "A claim [1].", critique: critique(8) },
  ],
};

describe("ResultView", () => {
  it("shows the score of every draft in order", () => {
    render(<ResultView state={state} />);
    expect(screen.getByTestId("score-v1")).toHaveTextContent("v1 · 5/10");
    expect(screen.getByTestId("score-v2")).toHaveTextContent("v2 · 8/10");
  });

  it("scales each rubric bar to its score once it has grown", async () => {
    render(<ResultView state={state} />);
    await waitFor(() =>
      expect(screen.getAllByTestId("bar-accuracy")[0]).toHaveStyle({ transform: "scaleX(0.6)" }),
    );
    expect(screen.getAllByTestId("bar-citation_quality")[0]).toHaveStyle({
      transform: "scaleX(0.9)",
    });
  });

  it("separates cited sources from those only read", () => {
    render(<ResultView state={state} />);
    expect(screen.getByTestId("sources-cited")).toHaveTextContent("Cited paper");
    expect(screen.getByTestId("sources-cited")).not.toHaveTextContent("Unused paper");
    expect(screen.getByTestId("sources-uncited")).toHaveTextContent("Unused paper");
  });

  it("offers the final report as a download", () => {
    render(<ResultView state={state} />);
    const link = screen.getByRole("link", { name: /Download/ });
    expect(link).toHaveAttribute("download", "mrna-vaccines.md");
    expect(decodeURIComponent(link.getAttribute("href")!)).toContain("A claim [1].");
  });

  it("lists earlier drafts but not the final one", () => {
    render(<ResultView state={state} />);
    const drafts = screen.getByLabelText("Earlier drafts");
    expect(drafts).toHaveTextContent("Draft v1");
    expect(drafts).not.toHaveTextContent("Draft v2");
  });

  it("lists claims the sources do not support", () => {
    const flagged = {
      ...state,
      drafts: [
        state.drafts[0],
        {
          ...state.drafts[1],
          critique: critique(7, {
            unsupported_claims: [
              { claim: "Efficacy was 95%", source_id: 1, reason: "the source says 91%" },
              { claim: "Approved in 2019", source_id: null, reason: "no source" },
            ],
          }),
        },
      ],
    };
    render(<ResultView state={flagged} />);
    const panel = screen.getByLabelText("Unsupported claims");
    expect(panel).toHaveTextContent("2 claims the sources do not support");
    expect(panel).toHaveTextContent("Cites [1] — the source says 91%");
    expect(panel).toHaveTextContent("Uncited — no source");
  });

  it("renders nothing until a report exists", () => {
    const { container } = render(<ResultView state={initialState} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("builds a filename from the topic", () => {
    expect(markdownFilename("EU AI Act: enforcement!")).toBe("eu-ai-act-enforcement.md");
    expect(markdownFilename("???")).toBe("research-report.md");
  });
});
