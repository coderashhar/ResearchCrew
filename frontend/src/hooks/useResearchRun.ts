"use client";

import { useCallback, useEffect, useReducer, useRef } from "react";

import { readEvents } from "@/lib/sse";
import { initialState, runReducer, type RunState } from "@/lib/runReducer";
import type { SavedRun } from "@/lib/types";

export type UseResearchRun = {
  state: RunState;
  running: boolean;
  start: (topic: string) => Promise<void>;
  load: (run: SavedRun) => void;
};

export function useResearchRun(saved?: SavedRun): UseResearchRun {
  const [state, dispatch] = useReducer(runReducer, initialState);
  const abort = useRef<AbortController | null>(null);

  useEffect(() => {
    if (saved) dispatch({ type: "load", run: saved });
  }, [saved]);

  // Leaving the page mid-run must not leave the response open.
  useEffect(() => () => abort.current?.abort(), []);

  const start = useCallback(async (topic: string) => {
    abort.current?.abort();
    const controller = new AbortController();
    abort.current = controller;
    dispatch({ type: "start", topic });

    try {
      const response = await fetch("/api/research", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic }),
        signal: controller.signal,
      });

      if (!response.ok || !response.body) {
        dispatch({ type: "failed", message: await errorMessage(response) });
        return;
      }

      for await (const event of readEvents(response.body)) {
        dispatch({ type: "event", event });
        // A permalink from the first event: a reload keeps the report.
        if (event.name === "run" && typeof window !== "undefined") {
          window.history.replaceState(null, "", `/r/${event.data.id}`);
        }
      }
    } catch (error) {
      if (controller.signal.aborted) return;
      dispatch({ type: "failed", message: describe(error) });
    }
  }, []);

  const load = useCallback((run: SavedRun) => dispatch({ type: "load", run }), []);

  return { state, running: state.step !== "idle" && state.step !== "done", start, load };
}

async function errorMessage(response: Response): Promise<string> {
  if (response.status === 429) {
    return "That is five research runs this hour. Try again later.";
  }
  try {
    const body = await response.json();
    const detail = body?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg);
  } catch {
    // fall through to the generic message
  }
  return `The server returned ${response.status}.`;
}

function describe(error: unknown): string {
  return error instanceof Error ? error.message : "The connection was lost.";
}
