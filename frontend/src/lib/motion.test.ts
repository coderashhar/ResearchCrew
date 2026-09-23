import { readFileSync, readdirSync, statSync } from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

/**
 * Motion rules enforced across the source, so a stray `transition: all`
 * or an un-gated hover cannot creep back in one component at a time.
 */
const SRC = path.resolve(import.meta.dirname, "..");

function sourceFiles(dir = SRC): string[] {
  return readdirSync(dir).flatMap((entry) => {
    const full = path.join(dir, entry);
    if (statSync(full).isDirectory()) return sourceFiles(full);
    return /\.(tsx?|css)$/.test(entry) && !entry.includes(".test.") ? [full] : [];
  });
}

const files = sourceFiles().map((file) => ({
  name: path.relative(SRC, file),
  text: readFileSync(file, "utf8"),
}));

const css = files.find((f) => f.name.endsWith("globals.css"))!.text;

function offenders(pattern: RegExp) {
  return files.filter((f) => pattern.test(f.text)).map((f) => f.name);
}

describe("motion rules", () => {
  it("never animates every property", () => {
    expect(offenders(/transition:\s*all\b/)).toEqual([]);
    expect(offenders(/\btransition-all\b/)).toEqual([]);
  });

  it("never eases in, which delays the movement the eye is waiting for", () => {
    expect(offenders(/ease-in(?!-out)[^-]/)).toEqual([]);
  });

  it("never grows something out of nothing", () => {
    expect(offenders(/scale\(0\)|scaleX\(0\)(?!\s*[`"'])/)).toEqual([]);
  });

  it("keeps UI movement under 300ms", () => {
    const durations = [...css.matchAll(/--dur-[a-z]+:\s*(\d+)ms/g)].map((m) => Number(m[1]));
    expect(durations.length).toBeGreaterThan(0);
    expect(Math.max(...durations)).toBeLessThanOrEqual(300);
  });

  it("gates hover effects behind a real pointer", () => {
    const hoverBlocks = [...css.matchAll(/^\s*\.[\w-]+:hover/gm)];
    const gated = [...css.matchAll(/@media \(hover: hover\) and \(pointer: fine\)/g)];
    expect(hoverBlocks.length).toBeLessThanOrEqual(gated.length);
  });

  it("honours a reduced-motion preference", () => {
    expect(css).toMatch(/@media \(prefers-reduced-motion: reduce\)/);
    const blocks = [...css.matchAll(/@media \(prefers-reduced-motion: reduce\)/g)];
    expect(blocks.length).toBeGreaterThanOrEqual(2);
  });

  it("defines the motion tokens every component uses", () => {
    for (const token of ["--ease-out", "--ease-in-out", "--dur-press", "--dur-ui", "--dur-enter"]) {
      expect(css).toContain(`${token}:`);
    }
  });

  it("presses buttons in, so a click is acknowledged", () => {
    expect(css).toMatch(/\.pressable:active:not\(:disabled\)\s*{\s*transform: scale\(0\.9\d\)/);
  });
});
