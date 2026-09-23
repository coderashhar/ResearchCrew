import { expect, test } from "@playwright/test";

import fixtures from "./fixtures.json" with { type: "json" };

const { runId, topic } = fixtures;
const DIR = "../docs/images";

// Not assertions: this spec produces the README images from the same
// stubbed run the other browser tests use.
test.use({ viewport: { width: 1100, height: 900 } });

test("capture the README screenshots", async ({ page }) => {
  await page.goto("/");
  await page.screenshot({ path: `${DIR}/landing.png` });

  await page.getByLabel("Research topic").fill(topic);
  await page.getByRole("button", { name: "Start research" }).click();
  await expect(page.getByLabel("Run log")).toContainText("nature.com");
  await page.screenshot({ path: `${DIR}/running.png` });

  await expect(page.getByLabel("Research report")).toBeVisible();
  await expect(page).toHaveURL(new RegExp(`/r/${runId}$`));
  await page.getByLabel("Source 1: First paper").click();
  await expect(page.locator(".citation-popover")).toBeVisible();
  // Let the staggered rubric bars finish, so the image is not a freeze
  // frame of them mid-growth.
  await page.waitForTimeout(600);
  await page.screenshot({ path: `${DIR}/report.png`, fullPage: true });
});
