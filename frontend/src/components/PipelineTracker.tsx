import type { Step } from "@/lib/runReducer";

const STEPS: { id: Step; label: string }[] = [
  { id: "plan", label: "Plan" },
  { id: "research", label: "Read" },
  { id: "write", label: "Write" },
  { id: "critique", label: "Check" },
];

type NodeState = "waiting" | "running" | "done";
type LinkState = "waiting" | "active" | "done";

export function nodeState(step: Step, index: number): NodeState {
  if (step === "idle") return "waiting";
  if (step === "done") return "done";
  const current = STEPS.findIndex((s) => s.id === step);
  if (index < current) return "done";
  return index === current ? "running" : "waiting";
}

export function linkState(step: Step, index: number): LinkState {
  const before = nodeState(step, index);
  if (before !== "done") return "waiting";
  return nodeState(step, index + 1) === "waiting" ? "waiting" : "done";
}

export function PipelineTracker({ step, revision }: { step: Step; revision: number }) {
  return (
    <div className="flex flex-wrap items-center gap-2" aria-label="Research progress">
      {STEPS.map((node, i) => (
        <div key={node.id} className="flex items-center gap-2">
          <div data-state={nodeState(step, i)} data-testid={`node-${node.id}`} className="node text-sm">
            {node.label}
          </div>
          {i < STEPS.length - 1 && (
            <span
              data-state={step === "idle" ? "waiting" : linkState(step, i)}
              data-testid={`link-${node.id}`}
              className="connector"
              aria-hidden
            />
          )}
        </div>
      ))}

      {revision > 0 && (
        <span className="enter ml-1 rounded-full border border-amber/40 px-2 py-0.5 text-xs text-amber">
          revision {revision}
        </span>
      )}
    </div>
  );
}
