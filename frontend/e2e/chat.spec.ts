import { expect, test } from "@playwright/test";
import { DEFAULT_PASSWORD, login } from "./helpers";

// The realtime gateway isn't part of the e2e stack (NEXT_PUBLIC_REALTIME_URL is
// unset), so this exercises the REST path: send persists + the refetch shows it.
test("send a message in a project's chat room", async ({ page }) => {
  await login(page, "maker", DEFAULT_PASSWORD);

  await page.goto("/projects/maker/coolproject");
  await expect(page.getByRole("heading", { name: "maker/coolproject" })).toBeVisible();

  // Switch to the Chat tab.
  await page.getByRole("button", { name: "Chat" }).click();
  await expect(page.getByRole("heading", { name: "Project chat" })).toBeVisible();

  const message = `gm team ${Date.now()}`;
  await page.getByPlaceholder(/Message #coolproject/).fill(message);
  await page.getByRole("button", { name: "Send" }).click();

  await expect(page.getByText(message)).toBeVisible();
});
