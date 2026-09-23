import { expect, test } from "@playwright/test";

import fixtures from "./fixtures.json" with { type: "json" };

const { runId, topic } = fixtures;

async function startRun(page: import("@playwright/test").Page) {
  await page.goto("/");
  await page.getByLabel("Research topic").fill(topic);
  await page.getByRole("button", { name: "Start research" }).click();
}

test("a run streams, finishes and keeps its own URL", async ({ page }) => {
  await startRun(page);

  await expect(page.getByLabel("Research report")).toContainText("A stronger claim");
  await expect(page.getByTestId("score-v1")).toHaveText("v1 · 5/10");
  await expect(page.getByTestId("score-v2")).toHaveText("v2 · 8/10");

  for (const node of ["plan", "research", "write", "critique"]) {
    await expect(page.getByTestId(`node-${node}`)).toHaveAttribute("data-state", "done");
  }

  // The run got its own address while it was still running.
  await expect(page).toHaveURL(new RegExp(`/r/${runId}$`));
});

test("the live log shows what the agents are doing", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Research topic").fill(topic);
  // Watch the log from the moment the run starts: it is replaced by the
  // report as soon as the run finishes.
  const log = page.getByLabel("Run log");
  await page.getByRole("button", { name: "Start research" }).click();
  await expect(log).toContainText("Search: how mRNA works");
  await expect(log).toContainText("nature.com");
});

test("a citation chip opens its source", async ({ page }) => {
  await startRun(page);
  await expect(page.getByLabel("Research report")).toBeVisible();

  await page.getByLabel("Source 2: Second paper").click();
  await expect(page.getByRole("link", { name: "Open source" })).toHaveAttribute(
    "href",
    "https://who.int/b",
  );
});

test("a finished run is served from its permalink", async ({ page }) => {
  await page.goto(`/r/${runId}`);

  await expect(page.getByRole("heading", { name: topic })).toBeVisible();
  await expect(page.getByLabel("Research report")).toContainText("A stronger claim");
  await expect(page.getByTestId("sources-cited")).toContainText("First paper");
  await expect(page.getByLabel("Earlier drafts")).toContainText("Draft v1");
});

test("an unknown run is not found", async ({ page }) => {
  const response = await page.goto("/r/00000000-0000-0000-0000-000000000000");
  expect(response?.status()).toBe(404);
});
