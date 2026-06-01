"use client";

import { PostCard } from "@/components/post-card";
import { EmptyState, Spinner } from "@/components/ui/card";
import { useProjectPosts, useRepo } from "@/lib/queries";
import {
  ExternalLink,
  GitFork,
  CircleDot,
  Star,
} from "lucide-react";
import { useParams } from "next/navigation";

export default function ProjectPage() {
  const params = useParams<{ owner: string; name: string }>();
  const { owner, name } = params;
  const { data: repo, isLoading, isError } = useRepo(owner, name);
  const { data: posts } = useProjectPosts(`${owner}/${name}`);

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <Spinner />
      </div>
    );
  }

  if (isError || !repo) {
    return <EmptyState title="Project not found" description={`${owner}/${name}`} />;
  }

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-border-strong bg-surface p-5">
        <div className="flex items-start justify-between gap-3">
          <h1 className="font-mono text-xl font-semibold">
            {repo.owner_login}/<span className="text-accent">{repo.name}</span>
          </h1>
          <a
            href={repo.html_url}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1 text-sm text-muted hover:text-fg"
          >
            GitHub <ExternalLink className="h-3.5 w-3.5" />
          </a>
        </div>

        {repo.description && (
          <p className="mt-2 text-sm text-fg/90">{repo.description}</p>
        )}

        {repo.topics.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {repo.topics.map((t) => (
              <span
                key={t}
                className="rounded-full bg-accent-soft px-2.5 py-0.5 text-xs text-accent"
              >
                {t}
              </span>
            ))}
          </div>
        )}

        <div className="mt-4 flex flex-wrap gap-5 text-sm text-muted">
          {repo.language && <span>{repo.language}</span>}
          <span className="flex items-center gap-1.5">
            <Star className="h-4 w-4" />
            {repo.stargazers_count.toLocaleString()}
          </span>
          <span className="flex items-center gap-1.5">
            <GitFork className="h-4 w-4" />
            {repo.forks_count.toLocaleString()}
          </span>
          <span className="flex items-center gap-1.5">
            <CircleDot className="h-4 w-4" />
            {repo.open_issues_count.toLocaleString()} issues
          </span>
        </div>
      </div>

      <div>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-faint">
          Devlogs
        </h2>
        <div className="space-y-4">
          {posts && posts.results.length > 0 ? (
            posts.results.map((post) => <PostCard key={post.id} post={post} />)
          ) : (
            <EmptyState
              title="No devlogs yet"
              description="Be the first to post an update about this project."
            />
          )}
        </div>
      </div>
    </div>
  );
}
