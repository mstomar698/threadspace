"use client";

import { Card, Spinner } from "@/components/ui/card";
import { errorMessage } from "@/lib/api";
import { useGithubCallback } from "@/lib/queries";
import { CircleCheck, CircleX } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef } from "react";

function CallbackInner() {
  const params = useSearchParams();
  const callback = useGithubCallback();
  const started = useRef(false);

  const code = params.get("code");
  const state = params.get("state");
  const oauthError = params.get("error_description") ?? params.get("error");

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    if (oauthError || !code || !state) return;
    callback.mutate(
      { code, state },
      {
        onSuccess: () => {
          window.location.replace("/settings");
        },
      },
    );
  }, [callback, code, state, oauthError]);

  const failed = oauthError || !code || !state || callback.isError;

  return (
    <Card className="flex flex-col items-center gap-3 p-10 text-center">
      {failed ? (
        <>
          <CircleX className="h-8 w-8 text-danger" />
          <p className="font-medium">Could not connect GitHub</p>
          <p className="max-w-sm text-sm text-muted">
            {oauthError
              ? String(oauthError)
              : !code || !state
                ? "Missing authorization details in the callback."
                : errorMessage(callback.error, "The authorization could not be completed.")}
          </p>
          <Link href="/settings" className="text-sm text-accent hover:underline">
            Back to settings
          </Link>
        </>
      ) : (
        <>
          {callback.isSuccess ? (
            <CircleCheck className="h-8 w-8 text-success" />
          ) : (
            <Spinner />
          )}
          <p className="font-medium">
            {callback.isSuccess ? "Connected!" : "Finishing GitHub connection..."}
          </p>
          <p className="text-sm text-muted">Hang tight, redirecting you back.</p>
        </>
      )}
    </Card>
  );
}

export default function GithubCallbackPage() {
  return (
    <Suspense
      fallback={
        <Card className="flex justify-center p-10">
          <Spinner />
        </Card>
      }
    >
      <CallbackInner />
    </Suspense>
  );
}
