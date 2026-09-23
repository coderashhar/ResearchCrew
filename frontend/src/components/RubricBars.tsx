"use client";

import { useEffect, useRef, useState } from "react";

import { RUBRIC, type Critique } from "@/lib/types";

/**
 * Five criteria, so a score says what was wrong rather than only how
 * wrong. Bars grow once, on first reveal: replaying the fill on every
 * re-render would be noise.
 */
export function RubricBars({ critique }: { critique: Critique }) {
  const [grown, setGrown] = useState(false);
  const timer = useRef<number | null>(null);

  useEffect(() => {
    timer.current = window.requestAnimationFrame(() => setGrown(true));
    return () => {
      if (timer.current !== null) window.cancelAnimationFrame(timer.current);
    };
  }, []);

  return (
    <dl className="space-y-2" aria-label="Quality rubric">
      {RUBRIC.map(([key, label], i) => {
        const score = critique[key];
        return (
          <div key={key} className="flex items-center gap-3 text-sm">
            <dt className="w-24 shrink-0 text-muted">{label}</dt>
            <dd className="flex flex-1 items-center gap-3">
              <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/5">
                <div
                  data-testid={`bar-${key}`}
                  data-grown={grown}
                  className="h-full origin-left rounded-full bg-indigo"
                  style={{
                    transform: `scaleX(${grown ? score / 10 : 0})`,
                    transition: `transform var(--dur-enter) var(--ease-out) ${i * 30}ms`,
                  }}
                />
              </div>
              <span className="w-8 text-right tabular-nums text-muted">{score}</span>
            </dd>
          </div>
        );
      })}
    </dl>
  );
}
