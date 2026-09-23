"use client";

import { useState } from "react";

export function TopicForm({
  running,
  onSubmit,
}: {
  running: boolean;
  onSubmit: (topic: string) => void;
}) {
  const [topic, setTopic] = useState("");
  const empty = topic.trim().length === 0;

  return (
    <form
      className="flex flex-col gap-3 sm:flex-row"
      onSubmit={(e) => {
        e.preventDefault();
        if (!empty && !running) onSubmit(topic.trim());
      }}
    >
      <input
        aria-label="Research topic"
        placeholder="What should the agents research?"
        maxLength={300}
        value={topic}
        disabled={running}
        onChange={(e) => setTopic(e.target.value)}
        className="card flex-1 px-4 py-3 text-fg placeholder:text-faint outline-none focus:border-indigo/50"
        style={{ transition: "border-color var(--dur-ui) var(--ease-out)" }}
      />
      <button
        type="submit"
        disabled={empty || running}
        className="pressable rounded-2xl bg-indigo px-6 py-3 font-medium text-white disabled:opacity-40"
      >
        {running ? "Researching…" : "Start research"}
      </button>
    </form>
  );
}
