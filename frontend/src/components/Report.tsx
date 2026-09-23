"use client";

import { Fragment, type ReactNode } from "react";
import ReactMarkdown from "react-markdown";

import { CitationChip } from "@/components/CitationChip";
import type { SourceSummary } from "@/lib/types";

const CITATION = /\[(\d+(?:\s*,\s*\d+)*)\]/g;

/**
 * Replaces [n] and [n, m] in text with chips for the sources they name.
 * A number with no source stays as plain text rather than a dead chip.
 */
export function withCitations(text: string, byId: Map<number, SourceSummary>): ReactNode[] {
  const parts: ReactNode[] = [];
  let cursor = 0;

  for (const match of text.matchAll(CITATION)) {
    const ids = match[1].split(",").map((n) => Number(n.trim()));
    const sources = ids.map((id) => byId.get(id)).filter((s): s is SourceSummary => !!s);

    parts.push(text.slice(cursor, match.index));
    cursor = match.index + match[0].length;

    if (sources.length === 0) {
      parts.push(match[0]);
      continue;
    }
    parts.push(
      <Fragment key={`${match.index}`}>
        {sources.map((source) => (
          <CitationChip key={source.id} source={source} />
        ))}
      </Fragment>,
    );
  }

  parts.push(text.slice(cursor));
  return parts;
}

function citeChildren(children: ReactNode, byId: Map<number, SourceSummary>): ReactNode {
  if (typeof children === "string") return withCitations(children, byId);
  if (Array.isArray(children)) {
    return children.map((child, i) =>
      typeof child === "string" ? (
        <Fragment key={i}>{withCitations(child, byId)}</Fragment>
      ) : (
        child
      ),
    );
  }
  return children;
}

export function Report({ report, sources }: { report: string; sources: SourceSummary[] }) {
  const byId = new Map(sources.map((s) => [s.id, s]));
  const cite = (children: ReactNode) => citeChildren(children, byId);

  return (
    <article className="card space-y-4 p-6 leading-relaxed" aria-label="Research report">
      <ReactMarkdown
        components={{
          h1: ({ children }) => <h1 className="text-2xl font-semibold">{cite(children)}</h1>,
          h2: ({ children }) => <h2 className="text-xl font-semibold">{cite(children)}</h2>,
          h3: ({ children }) => <h3 className="text-lg font-semibold">{cite(children)}</h3>,
          p: ({ children }) => <p>{cite(children)}</p>,
          li: ({ children }) => <li className="ml-5 list-disc">{cite(children)}</li>,
          a: ({ children, href }) => (
            <a
              href={href}
              target="_blank"
              rel="noreferrer noopener"
              className="text-cyan underline underline-offset-2"
            >
              {children}
            </a>
          ),
        }}
      >
        {report}
      </ReactMarkdown>
    </article>
  );
}
