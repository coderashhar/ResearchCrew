import { expect, test } from "@playwright/test";

import fixtures from "./fixtures.json" with { type: "json" };

const { topic } = fixtures;

test("a button presses in when it is clicked", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Research topic").fill(topic);
  const button = page.getByRole("button", { name: "Start research" });

  const box = (await button.boundingBox())!;
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await page.mouse.down();

  // The press is a 140ms transition, so wait for it to settle.
  await expect
    .poll(() => button.evaluate((el) => getComputedStyle(el).transform))
    .toBe("matrix(0.97, 0, 0, 0.97, 0, 0)");

  await page.mouse.up();
});

test("reduced motion stops the looping animations", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  await page.getByLabel("Research topic").fill(topic);
  await page.getByRole("button", { name: "Start research" }).click();

  await expect(page.getByLabel("Research report")).toBeVisible();

  const pulse = await page.evaluate(
    (selector: string) => getComputedStyle(document.querySelector(selector)!, "::after").animationName,
    '[data-testid="node-plan"]',
  );
  expect(pulse).toBe("none");

  // Press feedback also stops moving, but the button still responds visually.
  const button = page.getByRole("button", { name: "Start research" });
  const box = (await button.boundingBox())!;
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await page.mouse.down();
  expect(await button.evaluate((el) => getComputedStyle(el).transform)).toBe("none");
  await page.mouse.up();
});

test("a citation popover opens from the chip that was clicked", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Research topic").fill(topic);
  await page.getByRole("button", { name: "Start research" }).click();
  await expect(page.getByLabel("Research report")).toBeVisible();

  await page.getByLabel("Source 1: First paper").click();
  const popover = page.locator(".citation-popover");
  await expect(popover).toBeVisible();

  const { origin, fromTrigger, box } = await popover.evaluate((el) => ({
    origin: getComputedStyle(el).transformOrigin,
    fromTrigger: getComputedStyle(el).getPropertyValue(
      "--radix-popover-content-transform-origin",
    ),
    box: { width: el.clientWidth, height: el.clientHeight },
  }));

  // Radix resolves the origin to the trigger; the default is the centre.
  expect(fromTrigger.trim()).not.toBe("");
  const [x, y] = origin.split(" ").map(parseFloat);
  expect([x, y]).not.toEqual([box.width / 2, box.height / 2]);
});
