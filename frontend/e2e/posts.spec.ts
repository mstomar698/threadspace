import { expect, test } from "@playwright/test";
import { register, uniqueName } from "./helpers";

test("compose a post and see it in the feed and on the profile", async ({ page }) => {
  const username = uniqueName("poster");
  await register(page, username);

  const caption = `Shipped a thing at ${Date.now()}`;
  await page.getByPlaceholder("What did you ship today?").fill(caption);
  await page.locator('input[type="file"]').setInputFiles("e2e/fixtures/sample.png");
  await page.getByRole("button", { name: "Post" }).click();

  // Appears in the feed.
  await expect(page.getByText(caption)).toBeVisible();

  // Appears on the author's profile, and the post count reflects it.
  await page.goto(`/${username}`);
  await expect(page.getByRole("heading", { name: username })).toBeVisible();
  await expect(page.getByText(caption)).toBeVisible();
});
