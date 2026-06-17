"use client";

import { Button } from "@/components/ui/button";
import { errorMessage, GITHUB_NONCE_KEY } from "@/lib/api";
import { useGithubLogin } from "@/lib/queries";
import { GitBranch } from "lucide-react";
import { useState } from "react";

/** "Continue with GitHub" — starts the OAuth sign-in/sign-up flow. */
export function GithubLoginButton({ label }: { label: string }) {
  const login = useGithubLogin();
  const [error, setError] = useState<string | null>(null);

  const start = () => {
    setError(null);
    login.mutate(undefined, {
      onSuccess: ({ authorize_url, nonce }) => {
        // Stored here and echoed back on the callback to bind the OAuth state
        // to this browser (login CSRF guard).
        sessionStorage.setItem(GITHUB_NONCE_KEY, nonce);
        window.location.href = authorize_url;
      },
      onError: (err) =>
        setError(errorMessage(err, "GitHub sign-in is unavailable right now.")),
    });
  };

  return (
    <div>
      <Button
        type="button"
        variant="secondary"
        className="w-full justify-center"
        loading={login.isPending}
        onClick={start}
      >
        <GitBranch className="h-4 w-4" />
        {label}
      </Button>
      {error && <p className="mt-2 text-sm text-danger">{error}</p>}
    </div>
  );
}
