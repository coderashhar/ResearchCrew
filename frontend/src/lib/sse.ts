import type { ResearchEvent } from "./types";

/**
 * Turns a byte stream of server-sent events into parsed events.
 *
 * Events arrive split across arbitrary chunk boundaries, so a partial
 * block is held back until its blank-line terminator shows up.
 */
export class SseParser {
  private buffer = "";

  push(chunk: string): ResearchEvent[] {
    this.buffer += chunk;
    const events: ResearchEvent[] = [];

    let split: number;
    while ((split = this.buffer.indexOf("\n\n")) !== -1) {
      const block = this.buffer.slice(0, split);
      this.buffer = this.buffer.slice(split + 2);
      const event = parseBlock(block);
      if (event) events.push(event);
    }
    return events;
  }
}

function parseBlock(block: string): ResearchEvent | null {
  let name = "";
  const dataLines: string[] = [];

  for (const line of block.split("\n")) {
    if (line.startsWith(":")) continue; // heartbeat comment
    if (line.startsWith("event:")) name = line.slice(6).trim();
    else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
  }
  if (!name || dataLines.length === 0) return null;

  try {
    return { name, data: JSON.parse(dataLines.join("\n")) } as ResearchEvent;
  } catch {
    return {
      name: "error",
      data: { message: "The server sent an event this page could not read." },
    };
  }
}

export async function* readEvents(
  body: ReadableStream<Uint8Array>,
): AsyncGenerator<ResearchEvent> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  const parser = new SseParser();

  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      for (const event of parser.push(decoder.decode(value, { stream: true }))) {
        yield event;
      }
    }
  } finally {
    reader.releaseLock();
  }
}
