import { expect, test } from "@playwright/test";
import { API_URL, DEFAULT_PASSWORD, login } from "./helpers";

const MAKER_POST = "Shipped the first cut of coolproject 🚀";

test("seeded maker's projects appear on the profile, projects page, and detail", async ({
  page,
}) => {
  // "maker" is seeded with the password from seed_e2e.
  await login(page, "maker", DEFAULT_PASSWORD);

  // Projects page lists the maker's own imported repo.
  await page.goto("/projects");
  await expect(page.locator('a[href="/projects/maker/coolproject"]')).toBeVisible();

  // The profile shows a Projects section. (The repo also links from the post's
  // attached-repo card, so there can be more than one matching link.)
  await page.goto("/maker");
  await expect(page.getByRole("heading", { name: "Projects" })).toBeVisible();
  await expect(
    page.locator('a[href="/projects/maker/coolproject"]').first(),
  ).toBeVisible();

  // The project detail page shows the repo and its devlog.
  await page.goto("/projects/maker/coolproject");
  await expect(page.getByRole("heading", { name: "maker/coolproject" })).toBeVisible();
  await expect(page.getByText(MAKER_POST)).toBeVisible();
});

test("post a devlog directly from a project page", async ({ page }) => {
  await login(page, "maker", DEFAULT_PASSWORD);
  await page.goto("/projects/maker/coolproject");
  await expect(page.getByRole("heading", { name: "maker/coolproject" })).toBeVisible();

  const caption = `Update from the project page ${Date.now()}`;
  const composer = page.getByPlaceholder(/Share an update on coolproject/);
  await composer.fill(caption);
  await page.locator('input[type="file"]').setInputFiles("e2e/fixtures/sample.png");
  await page.getByRole("button", { name: "Post" }).click();

  // Wait for the composer to clear (post succeeded) before asserting, so we
  // don't match the still-filled textarea or race the in-flight upload.
  await expect(composer).toHaveValue("");
  // The new devlog appears in the project's Devlogs list.
  await expect(page.getByText(caption)).toBeVisible();
});

test("sign in with GitHub (stubbed) then import repositories", async ({ page, request }) => {
  // Obtain a valid signed OAuth state from the API, then drive the callback
  // directly — we can't (and don't need to) round-trip through github.com.
  const res = await request.get(`${API_URL}/api/v1/github/oauth/login-url/`);
  expect(res.ok()).toBeTruthy();
  const { authorize_url, nonce } = await res.json();
  const state = new URL(authorize_url).searchParams.get("state");
  expect(state).toBeTruthy();
  expect(nonce).toBeTruthy();

  // The SPA stores the nonce in sessionStorage before redirecting to GitHub;
  // seed it so the callback echoes it back (login CSRF guard).
  await page.addInitScript(
    ([key, value]) => sessionStorage.setItem(key, value),
    ["ts_gh_nonce", nonce as string],
  );
  await page.goto(`/github/callback?code=stub-code&state=${encodeURIComponent(state!)}`);

  // The stub creates and signs in "octocat", landing on the feed.
  await expect(page.getByRole("heading", { name: "Feed" })).toBeVisible({ timeout: 15_000 });

  // Settings shows the connected account; import the stubbed repos.
  await page.goto("/settings");
  await expect(page.getByText(/Connected as/)).toBeVisible();
  await page.getByRole("button", { name: /Import my repositories/ }).click();
  await expect(page.getByText(/Imported \d+ repositor/)).toBeVisible();

  // The imported projects now show up on the Projects page.
  await page.goto("/projects");
  await expect(page.locator('a[href="/projects/octocat/hello-world"]')).toBeVisible();
  await expect(page.locator('a[href="/projects/octocat/threadspace"]')).toBeVisible();
});
