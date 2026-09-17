import { expect, test } from "@playwright/test";

test("sign up, answer a Write from Dictation question and see a practice score", async ({ page }) => {
  // Browser speech synthesis is unreliable in headless Chrome, so skip the audio playback.
  await page.addInitScript(() => window.localStorage.setItem("pte:skip-audio", "1"));

  const email = `smoke-${Date.now()}@example.com`;
  await page.goto("/signup");
  await page.getByLabel("Your name").fill("Smoke Test");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("practice-password");
  await page.getByRole("button", { name: "Create account" }).click();

  await expect(page.getByRole("heading", { name: "Your PTE Academic readiness" })).toBeVisible();
  await page.getByRole("button", { name: "Start 15 Write from Dictation questions" }).click();

  await expect(page).toHaveURL(/\/practice\/\d+\?q=1/);
  await expect(page.getByText("Question 1 of 15")).toBeVisible();
  await expect(page.getByText("Time remaining")).toBeVisible({ timeout: 10_000 });

  await page.getByLabel("Type the sentence you hear").fill("Students submit their work online before the deadline");
  await page.getByRole("button", { name: "Submit answer" }).click();

  const result = page.getByRole("region", { name: "Your score" });
  await expect(result).toBeVisible();
  await expect(result.getByText("Practice score")).toBeVisible();
  await expect(result.getByText(/\d+%/)).toBeVisible();
  await expect(page.getByText("The sentence was:")).toBeVisible();
  await expect(page.getByRole("button", { name: "Next question" })).toBeVisible();
});
