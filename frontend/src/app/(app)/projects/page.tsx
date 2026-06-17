"use client";

import { RepoCard } from "@/components/repo-card";
import { EmptyState, Spinner } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useMyRepos, useRepoSearch } from "@/lib/queries";
import { FolderGit2, Search } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

export default function ProjectsPage() {
  const [q, setQ] = useState("");
  const searching = q.trim().length > 0;
  const mine = useMyRepos();
  const search = useRepoSearch(q);
  const active = searching ? search : mine;
  const repos = active.data?.results ?? [];

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Projects</h1>
        <p className="text-sm text-muted">
          Your imported repositories. Search to explore every project on ThreadSpace.
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
        ) : (
          <EmptyState
            icon={<FolderGit2 className="h-8 w-8" />}
            title="No projects yet"
            description="Connect GitHub and import your repositories from Settings to see them here."
          />
        )
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {repos.map((repo) => (
            <RepoCard key={repo.full_name} repo={repo} />
          ))}
        </div>
      )}

      {!searching && repos.length > 0 && (
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
