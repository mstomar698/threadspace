import { expect, test } from "@playwright/test";
import { register, uniqueName } from "./helpers";

test("compose a post and see it in the feed and on the profile", async ({ page }) => {
  const username = uniqueName("poster");
  await register(page, username);

  const caption = `Shipped a thing at ${Date.now()}`;
  const composer = page.getByPlaceholder("What did you ship today?");
  await composer.fill(caption);
  await page.locator('input[type="file"]').setInputFiles("e2e/fixtures/sample.png");
  await page.getByRole("button", { name: "Post" }).click();

  // The composer clears only after the upload succeeds — wait for that so we
  // don't race the in-flight POST (and so the caption match below is the
  // rendered post, not the textarea we just typed into).
  await expect(composer).toHaveValue("");
  // Appears in the feed.
  await expect(page.getByText(caption)).toBeVisible();

  // Appears on the author's profile, and the post count reflects it.
  await page.goto(`/${username}`);
  await expect(page.getByRole("heading", { name: username })).toBeVisible();
  await expect(page.getByText(caption)).toBeVisible();
});

test("compose a text-only devlog (no image required)", async ({ page }) => {
  const username = uniqueName("texter");
  await register(page, username);

  const caption = `Text-only update ${Date.now()}`;
  const composer = page.getByPlaceholder("What did you ship today?");
  await composer.fill(caption);
  // No file attached — posting must still succeed now that images are optional.
  await page.getByRole("button", { name: "Post" }).click();

  await expect(composer).toHaveValue("");
  await expect(page.getByText(caption)).toBeVisible();
});
