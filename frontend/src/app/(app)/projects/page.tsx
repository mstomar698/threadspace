"use client";

import { RepoCard } from "@/components/repo-card";
import { LoadMore } from "@/components/load-more";
import { EmptyState, Spinner } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useAllRepos, useMyRepos, useRepoSearch } from "@/lib/queries";
import { cn } from "@/lib/utils";
import { FolderGit2, Search } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

export default function ProjectsPage() {
  const [q, setQ] = useState("");
  const [scope, setScope] = useState<"all" | "mine">("all");
  const searching = q.trim().length > 0;
  const all = useAllRepos();
  const mine = useMyRepos();
  const search = useRepoSearch(q);
  // Searching always spans every project; otherwise honour the All/Mine scope.
  const active = searching ? search : scope === "mine" ? mine : all;
  const repos = active.data?.pages.flatMap((p) => p.results) ?? [];

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Projects</h1>
        <p className="text-sm text-muted">
          Every project on ThreadSpace — imported by makers and the trending
          catalogue. Search to find any repo.
        </p>
      </div>

      <div className="relative">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-faint" />
        <Input
          className="pl-9"
          placeholder="Search all projects…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
      </div>

      {!searching && (
        <div className="flex gap-1">
          {(["all", "mine"] as const).map((s) => (
            <button
              key={s}
              onClick={() => setScope(s)}
              className={cn(
                "rounded-full px-3 py-1 text-sm font-medium transition-colors",
                scope === s
                  ? "bg-accent-soft text-accent"
                  : "text-muted hover:bg-surface-2 hover:text-fg",
              )}
            >
              {s === "all" ? "All projects" : "My projects"}
            </button>
          ))}
        </div>
      )}

      {active.isLoading ? (
        <div className="flex justify-center py-16">
          <Spinner />
        </div>
      ) : repos.length === 0 ? (
        searching ? (
          <EmptyState
            icon={<Search className="h-8 w-8" />}
            title="No projects match"
            description={`Nothing found for “${q}”.`}
          />
        ) : scope === "mine" ? (
          <EmptyState
            icon={<FolderGit2 className="h-8 w-8" />}
            title="No projects yet"
            description="Connect GitHub and import your repositories from Settings."
          />
        ) : (
          <EmptyState
            icon={<FolderGit2 className="h-8 w-8" />}
            title="No projects yet"
            description="Be the first to import a repository from Settings."
          />
        )
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-2">
            {repos.map((repo) => (
              <RepoCard key={repo.full_name} repo={repo} />
            ))}
          </div>
          <LoadMore
            hasNextPage={active.hasNextPage}
            isFetchingNextPage={active.isFetchingNextPage}
            fetchNextPage={active.fetchNextPage}
          />
        </>
      )}

      {!searching && scope === "mine" && repos.length > 0 && (
        <p className="pt-1 text-center text-xs text-faint">
          Want more here?{" "}
          <Link href="/settings" className="text-accent hover:underline">
            Import repositories
          </Link>
        </p>
      )}
    </div>
  );
}
