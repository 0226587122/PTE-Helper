import { expect, test } from "@playwright/test";

test.describe("full mock test", () => {
  test.setTimeout(180_000);

  test("start, answer, resume, then see the score report", async ({ page }) => {
    // Headless Chrome can't reliably read text aloud, so skip the audio playback.
    await page.addInitScript(() => window.localStorage.setItem("pte:skip-audio", "1"));

    const email = `mock-${Date.now()}@example.com`;
    await page.goto("/signup");
    await page.getByLabel("Your name").fill("Mock Tester");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill("practice-password");
    await page.getByRole("button", { name: "Create account" }).click();
    await expect(page.getByRole("heading", { name: "Your PTE Academic readiness" })).toBeVisible();

    // The mock test is offered from the dashboard.
    await page.getByRole("link", { name: "Take a full mock test" }).click();
    await expect(page.getByRole("heading", { name: "Full mock test" })).toBeVisible();
    await expect(page.getByText(/About \d+ to \d+ minutes/)).toBeVisible();
    await expect(page.getByRole("heading", { name: "Part 1: Speaking and Writing" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Part 2: Reading" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Part 3: Listening" })).toBeVisible();

    await page.getByRole("button", { name: /^Start/ }).click();
    await expect(page).toHaveURL(/\/mock\/\d+\?q=1/);
    const setId = Number(page.url().match(/\/mock\/(\d+)/)![1]);

    // The unscored spoken introduction comes first, exactly as in the real test.
    await expect(page.getByRole("heading", { name: "Personal introduction" })).toBeVisible();
    await expect(page.getByText("This response is not scored.")).toBeVisible();
    await page.getByRole("button", { name: "Continue to Part 1" }).click();

    // Then the instructions for Part 1.
    await expect(page.getByRole("heading", { name: "Part 1: Speaking and Writing" })).toBeVisible();
    await page.getByRole("button", { name: /^Start part 1$/ }).click();

    // Question 1 is Read Aloud: a speaking item with its own clock.
    await expect(page.getByText("Question 1 of")).toBeVisible();
    await expect(page.getByText("Read Aloud").first()).toBeVisible();
    await expect(page.getByText("Time to answer")).toBeVisible();
    // No score is ever shown during the test.
    await expect(page.getByText("Practice score")).toHaveCount(0);

    await page.getByRole("button", { name: "Start recording now" }).click();
    await expect(page.getByText(/Recording… speak now/)).toBeVisible();
    await page.getByRole("button", { name: "Stop recording" }).click();

    // The test moves on by itself once the recording stops.
    await expect(page).toHaveURL(new RegExp(`/mock/${setId}\\?q=2`), { timeout: 30_000 });
    await expect(page.getByText("Question 2 of")).toBeVisible();

    // Reopening the test without a question number resumes where we left off.
    await page.goto(`/mock/${setId}`);
    await expect(page).toHaveURL(new RegExp(`/mock/${setId}\\?q=2`));

    // Finish early, as a student can, and check the report.
    const submitted = await page.evaluate(async (id) => {
      const response = await fetch(`/api/mock-tests/${id}/submit`, { method: "POST", credentials: "same-origin" });
      return response.status;
    }, setId);
    expect(submitted).toBe(200);

    await page.goto(`/mock/${setId}/report`);
    await expect(page.getByRole("heading", { name: "Full mock test" })).toBeVisible();
    await expect(page.getByText("Practice estimate").first()).toBeVisible();
    await expect(page.getByText("/ 90")).toBeVisible();
    await expect(page.getByRole("main").getByText(/not official Pearson PTE Academic results/)).toBeVisible();

    // Four communicative skills and the enabling skills, including the one we can't score.
    for (const skill of ["Listening", "Reading", "Speaking", "Writing"]) {
      await expect(page.getByText(skill, { exact: true }).first()).toBeVisible();
    }
    await expect(page.getByText("Oral fluency")).toBeVisible();
    await expect(page.getByText("Not scored in practice")).toBeVisible();

    // One row per part, and every question is reviewable.
    const parts = page.locator("table tbody tr");
    await expect(parts).toHaveCount(3);
    await expect(page.getByText("1. Read Aloud")).toBeVisible();
    await page.getByText("1. Read Aloud").click();
    await expect(page.getByRole("region", { name: "Your score" })).toBeVisible();

    // The finished test shows up on the dashboard.
    await page.goto("/");
    await expect(page.getByText("1 completed")).toBeVisible();
    await expect(page.getByRole("cell", { name: "Full mock test" })).toBeVisible();
  });
});
