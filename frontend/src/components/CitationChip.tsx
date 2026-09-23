"use client";

import * as Popover from "@radix-ui/react-popover";

import type { SourceSummary } from "@/lib/types";

/**
 * A citation the reader can check without leaving the sentence: the chip
 * opens the source it points at.
 */
export function CitationChip({ source }: { source: SourceSummary }) {
  return (
    <Popover.Root>
      <Popover.Trigger
        aria-label={`Source ${source.id}: ${source.title}`}
        className="pressable mx-0.5 rounded-md border border-indigo/40 bg-indigo/10 px-1.5 text-[0.7em] align-super text-indigo"
      >
        {source.id}
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          sideOffset={6}
          collisionPadding={12}
          className="citation-popover card z-50 max-w-xs space-y-1 p-3 text-sm"
        >
          <p className="font-medium text-fg">{source.title}</p>
          <p className="text-faint">{source.domain}</p>
          <a
            href={source.url}
            target="_blank"
            rel="noreferrer noopener"
            className="inline-block text-cyan underline underline-offset-2"
          >
            Open source
          </a>
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}
