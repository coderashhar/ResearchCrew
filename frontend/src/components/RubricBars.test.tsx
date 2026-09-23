import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { RubricBars } from "./RubricBars";
import type { Critique } from "@/lib/types";

const critique: Critique = {
  accuracy: 6,
  coverage: 7,
  citation_quality: 9,
  clarity: 8,
  recency: 5,
  overall: 7,
  strengths: [],
  gaps: [],
  unsupported_claims: [],
  needs_more_research: false,
  followup_queries: [],
};

describe("RubricBars", () => {
  it("grows each bar to its score once", async () => {
    const { rerender } = render(<RubricBars critique={critique} />);
    const bar = screen.getByTestId("bar-accuracy");

    await waitFor(() => expect(bar).toHaveAttribute("data-grown", "true"));
    expect(bar).toHaveStyle({ transform: "scaleX(0.6)" });

    // A re-render must not replay the fill from zero.
    rerender(<RubricBars critique={critique} />);
    expect(screen.getByTestId("bar-accuracy")).toHaveAttribute("data-grown", "true");
  });

  it("staggers the bars so they read as a group, not a race", () => {
    render(<RubricBars critique={critique} />);
    expect(screen.getByTestId("bar-accuracy")).toHaveStyle({
      transition: "transform var(--dur-enter) var(--ease-out) 0ms",
    });
    expect(screen.getByTestId("bar-recency")).toHaveStyle({
      transition: "transform var(--dur-enter) var(--ease-out) 120ms",
    });
  });
});
