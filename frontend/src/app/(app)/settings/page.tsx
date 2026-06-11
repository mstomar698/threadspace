"use client";

import { Button } from "@/components/ui/button";
import { Card, Spinner } from "@/components/ui/card";
import { errorMessage } from "@/lib/api";
import {
  useConnectGithub,
  useDisconnectGithub,
  useGithubAccount,
  useImportRepos,
} from "@/lib/queries";
import { timeAgo } from "@/lib/utils";
import { Check, Download, GitBranch, Unlink } from "lucide-react";
import { useState } from "react";

export default function SettingsPage() {
  const { data, isLoading } = useGithubAccount();
  const connect = useConnectGithub();
  const disconnect = useDisconnectGithub();
  const importRepos = useImportRepos();
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const startConnect = () => {
    setError(null);
    connect.mutate(undefined, {
      onSuccess: (url) => {
        window.location.href = url;
      },
      onError: (err) => setError(errorMessage(err, "Could not start GitHub connect.")),
    });
  };

  const runImport = () => {
    setError(null);
    setMessage(null);
    importRepos.mutate(undefined, {
      onSuccess: (repos) =>
        setMessage(
          `Imported ${repos.length} ${repos.length === 1 ? "repository" : "repositories"}.`,
        ),
      onError: (err) => setError(errorMessage(err, "Import failed.")),
    });
  };

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Settings</h1>
        <p className="text-sm text-muted">Manage your connected accounts.</p>
      </div>

      <Card className="p-5">
        <div className="flex items-start gap-3">
          <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-surface-2 text-fg">
            <GitBranch className="h-5 w-5" />
          </span>
          <div className="min-w-0 flex-1">
            <h2 className="font-semibold">GitHub</h2>
            <p className="text-sm text-muted">
              Connect your GitHub account to import repositories and post your work.
            </p>

            {isLoading ? (
              <div className="mt-4 flex justify-center">
                <Spinner />
              </div>
            ) : data?.connected ? (
              <div className="mt-4 space-y-4">
                <div className="flex items-center gap-2 rounded-lg bg-success/10 px-3 py-2 text-sm text-success">
                  <Check className="h-4 w-4" />
                  <span>
                    Connected as <strong>@{data.login}</strong>
                    {data.connected_at && ` · ${timeAgo(data.connected_at)}`}
                  </span>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button onClick={runImport} loading={importRepos.isPending}>
                    <Download className="h-4 w-4" />
                    Import my repositories
                  </Button>
                  <Button
                    variant="danger"
                    onClick={() => disconnect.mutate()}
                    loading={disconnect.isPending}
                  >
                    <Unlink className="h-4 w-4" />
                    Disconnect
                  </Button>
                </div>
              </div>
            ) : (
              <div className="mt-4">
                <Button onClick={startConnect} loading={connect.isPending}>
                  <GitBranch className="h-4 w-4" />
                  Connect GitHub
                </Button>
              </div>
            )}

            {message && <p className="mt-3 text-sm text-success">{message}</p>}
            {error && <p className="mt-3 text-sm text-danger">{error}</p>}
          </div>
        </div>
      </Card>
    </div>
  );
}
