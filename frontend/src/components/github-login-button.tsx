"use client";

import { Button } from "@/components/ui/button";
import { errorMessage } from "@/lib/api";
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
      onSuccess: (url) => {
        window.location.href = url;
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
