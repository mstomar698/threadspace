import { expect, test } from "@playwright/test";
import { DEFAULT_PASSWORD, login, register, uniqueName } from "./helpers";

test("redirects anonymous visitors to the login page", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();
});

test("register, then log out and log back in", async ({ page }) => {
  const username = uniqueName("authuser");
  await register(page, username);

  // New accounts (following nobody) land on the discovery feed, which shows the
  // seeded maker's post rather than an empty state.
  await expect(page.getByText("Shipped the first cut of coolproject 🚀")).toBeVisible();

  // Log out (sidebar button has a "Log out" title).
  await page.getByRole("button", { name: "Log out" }).click();
  await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();

  await login(page, username, DEFAULT_PASSWORD);
  await expect(page.getByRole("heading", { name: "Feed" })).toBeVisible();
});

test("rejects bad credentials", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Username").fill("definitely-not-real");
  await page.getByLabel("Password", { exact: true }).fill("wrong-password-1");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByText(/No active account|Invalid credentials/)).toBeVisible();
});
