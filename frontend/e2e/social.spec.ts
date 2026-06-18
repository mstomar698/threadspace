import { expect, test } from "@playwright/test";
import { register, uniqueName } from "./helpers";

const MAKER_POST = "Shipped the first cut of coolproject 🚀";

test("find a maker, follow them, and see their post in the feed", async ({ page }) => {
  await register(page, uniqueName("follower"));

  // Explore now lives on the feed page: search, switch to the Users tab, and
  // open the seeded "maker" profile.
  await page.getByPlaceholder(/Search posts, people, projects/).fill("maker");
  await page.getByRole("button", { name: "Users" }).click();
  await page.locator('a[href="/maker"]').click();

  await expect(page.getByRole("heading", { name: "maker" })).toBeVisible();
  await page.getByRole("button", { name: "Follow" }).click();
  await expect(page.getByRole("button", { name: "Following" })).toBeVisible();

  // The maker's seeded devlog now shows up in the feed.
  await page.goto("/");
  await expect(page.getByText(MAKER_POST)).toBeVisible();
});
