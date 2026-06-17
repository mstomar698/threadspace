import { expect, type Page } from "@playwright/test";

export const API_URL = "http://127.0.0.1:8001";
export const DEFAULT_PASSWORD = "Passw0rd!123";

/** A username unique to this run that satisfies Django's validators. */
export function uniqueName(prefix = "tester"): string {
  return `${prefix}${Date.now().toString().slice(-7)}${Math.floor(Math.random() * 1000)}`;
}

export async function register(
  page: Page,
  username: string,
  password = DEFAULT_PASSWORD,
): Promise<void> {
  await page.goto("/register");
  await expect(page.getByRole("heading", { name: "Join ThreadSpace" })).toBeVisible();
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Email").fill(`${username}@example.com`);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByLabel("Confirm password").fill(password);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByRole("heading", { name: "Feed" })).toBeVisible();
}

export async function login(
  page: Page,
  username: string,
  password = DEFAULT_PASSWORD,
): Promise<void> {
  await page.goto("/login");
  await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Feed" })).toBeVisible();
}
