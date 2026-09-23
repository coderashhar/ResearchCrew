import type { Step } from "@/lib/runReducer";

const STEPS: { id: Step; label: string }[] = [
  { id: "plan", label: "Plan" },
  { id: "research", label: "Read" },
  { id: "write", label: "Write" },
  { id: "critique", label: "Check" },
];

type NodeState = "waiting" | "running" | "done";

export function nodeState(step: Step, index: number): NodeState {
  if (step === "idle") return "waiting";
  if (step === "done") return "done";
  const current = STEPS.findIndex((s) => s.id === step);
  if (index < current) return "done";
  return index === current ? "running" : "waiting";
}

const STYLES: Record<NodeState, string> = {
  waiting: "border-glass text-faint",
  running: "border-indigo text-fg",
  done: "border-emerald text-emerald",
};

export function PipelineTracker({ step, revision }: { step: Step; revision: number }) {
  return (
    <div className="flex flex-wrap items-center gap-2" aria-label="Research progress">
      {STEPS.map((node, i) => {
        const state = nodeState(step, i);
        return (
          <div key={node.id} className="flex items-center gap-2">
            <div
              data-state={state}
              data-testid={`node-${node.id}`}
              className={`rounded-xl border px-3 py-1.5 text-sm ${STYLES[state]}`}
              style={{ transition: "border-color var(--dur-ui) var(--ease-out), color var(--dur-ui) var(--ease-out)" }}
            >
              {node.label}
            </div>
            {i < STEPS.length - 1 && <span className="text-faint">·</span>}
          </div>
        );
      })}

      {revision > 0 && (
        <span className="enter ml-1 rounded-full border border-amber/40 px-2 py-0.5 text-xs text-amber">
          revision {revision}
        </span>
      )}
    </div>
  );
}
