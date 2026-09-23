import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PipelineTracker, nodeState } from "./PipelineTracker";
import type { Step } from "@/lib/runReducer";

const states = () =>
  ["plan", "research", "write", "critique"].map(
    (id) => screen.getByTestId(`node-${id}`).dataset.state,
  );

function renderAt(step: Step, revision = 0) {
  render(<PipelineTracker step={step} revision={revision} />);
  return states();
}

describe("PipelineTracker", () => {
  it("marks nothing before a run starts", () => {
    expect(renderAt("idle")).toEqual(["waiting", "waiting", "waiting", "waiting"]);
  });

  it("marks earlier nodes done and the current one running", () => {
    expect(renderAt("write")).toEqual(["done", "done", "running", "waiting"]);
  });

  it("marks every node done when the run finishes", () => {
    expect(renderAt("done")).toEqual(["done", "done", "done", "done"]);
  });

  it("shows the revision badge only while revising", () => {
    render(<PipelineTracker step="write" revision={0} />);
    expect(screen.queryByText(/revision/)).toBeNull();

    render(<PipelineTracker step="write" revision={2} />);
    expect(screen.getByText("revision 2")).toBeInTheDocument();
  });

  it("nodeState is a pure function of step and index", () => {
    expect(nodeState("critique", 0)).toBe("done");
    expect(nodeState("critique", 3)).toBe("running");
    expect(nodeState("plan", 1)).toBe("waiting");
  });
});
