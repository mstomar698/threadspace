"use client";

import { Card, Spinner } from "@/components/ui/card";
import { errorMessage, GITHUB_NONCE_KEY, tokenStore } from "@/lib/api";
import { useGithubCallback, useGithubLoginCallback } from "@/lib/queries";
import { CircleCheck, CircleX } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";

function CallbackInner() {
  const params = useSearchParams();
  const link = useGithubCallback();
  const signIn = useGithubLoginCallback();
  const started = useRef(false);
  // Logged in → we're linking GitHub to the current account; otherwise signing in.
  const [isLink] = useState(() => !!tokenStore.access);

  const code = params.get("code");
  const state = params.get("state");
  const oauthError = params.get("error_description") ?? params.get("error");

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    if (oauthError || !code || !state) return;

    if (isLink) {
      link.mutate(
        { code, state },
        { onSuccess: () => window.location.replace("/settings") },
      );
    } else {
      const nonce = sessionStorage.getItem(GITHUB_NONCE_KEY) ?? "";
      signIn.mutate(
        { code, state, nonce },
        {
          onSuccess: (result) => {
            sessionStorage.removeItem(GITHUB_NONCE_KEY);
            tokenStore.set(result);
            window.location.replace("/");
          },
        },
      );
    }
  }, [isLink, link, signIn, code, state, oauthError]);

  const active = isLink ? link : signIn;
  const failed = oauthError || !code || !state || active.isError;
  const verb = isLink ? "connect" : "sign in with";

  return (
    <Card className="flex flex-col items-center gap-3 p-10 text-center">
      {failed ? (
        <>
          <CircleX className="h-8 w-8 text-danger" />
          <p className="font-medium">Could not {verb} GitHub</p>
          <p className="max-w-sm text-sm text-muted">
            {oauthError
              ? String(oauthError)
              : !code || !state
                ? "Missing authorization details in the callback."
                : errorMessage(active.error, "The authorization could not be completed.")}
          </p>
          <Link
            href={isLink ? "/settings" : "/login"}
            className="text-sm text-accent hover:underline"
          >
            {isLink ? "Back to settings" : "Back to sign in"}
          </Link>
        </>
      ) : (
        <>
          {active.isSuccess ? (
            <CircleCheck className="h-8 w-8 text-success" />
          ) : (
            <Spinner />
          )}
          <p className="font-medium">
            {active.isSuccess
              ? isLink
                ? "Connected!"
                : "Signed in!"
              : isLink
                ? "Finishing GitHub connection..."
                : "Signing you in with GitHub..."}
          </p>
          <p className="text-sm text-muted">Hang tight, redirecting you.</p>
        </>
      )}
    </Card>
  );
}

export default function GithubCallbackPage() {
  return (
    <div className="grid min-h-screen place-items-center px-4">
      <div className="w-full max-w-sm">
        <Suspense
          fallback={
            <Card className="flex justify-center p-10">
              <Spinner />
            </Card>
          }
        >
          <CallbackInner />
        </Suspense>
      </div>
    </div>
  );
}
