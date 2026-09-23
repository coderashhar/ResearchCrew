import { describe, expect, it } from "vitest";

import { SseParser, readEvents } from "./sse";

const frame = (name: string, data: unknown) => `event: ${name}\ndata: ${JSON.stringify(data)}\n\n`;

describe("SseParser", () => {
  it("parses one complete event", () => {
    const events = new SseParser().push(frame("run", { id: "abc" }));
    expect(events).toEqual([{ name: "run", data: { id: "abc" } }]);
  });

  it("holds back an event split across chunks", () => {
    const parser = new SseParser();
    const text = frame("plan", { queries: [] });
    const cut = text.indexOf("data:") + 8;

    expect(parser.push(text.slice(0, cut))).toEqual([]);
    expect(parser.push(text.slice(cut))).toEqual([{ name: "plan", data: { queries: [] } }]);
  });

  it("parses several events in one chunk", () => {
    const events = new SseParser().push(
      frame("run", { id: "1" }) + frame("draft", { version: 1, report: "r" }),
    );
    expect(events.map((e) => e.name)).toEqual(["run", "draft"]);
  });

  it("ignores heartbeat comments", () => {
    const parser = new SseParser();
    expect(parser.push(": keep-alive\n\n")).toEqual([]);
    expect(parser.push(frame("run", { id: "x" }))).toHaveLength(1);
  });

  it("turns unreadable data into an error event instead of throwing", () => {
    const [event] = new SseParser().push("event: final\ndata: {oops\n\n");
    expect(event.name).toBe("error");
  });
});

describe("readEvents", () => {
  it("reads a whole response body", async () => {
    const encoder = new TextEncoder();
    const body = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(encoder.encode(frame("run", { id: "1" }).slice(0, 9)));
        controller.enqueue(
          encoder.encode(frame("run", { id: "1" }).slice(9) + ": keep-alive\n\n"),
        );
        controller.enqueue(encoder.encode(frame("error", { message: "boom" })));
        controller.close();
      },
    });

    const seen = [];
    for await (const event of readEvents(body)) seen.push(event);

    expect(seen.map((e) => e.name)).toEqual(["run", "error"]);
  });
});
