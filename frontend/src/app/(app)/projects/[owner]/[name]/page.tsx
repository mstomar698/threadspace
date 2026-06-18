"use client";

import { ChatPanel } from "@/components/chat-panel";
import { Composer } from "@/components/composer";
import { PostCard } from "@/components/post-card";
import { LoadMore } from "@/components/load-more";
import { EmptyState, Spinner } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { keys, useProjectPosts, useRepo } from "@/lib/queries";
import { useQueryClient } from "@tanstack/react-query";
import {
  ExternalLink,
  GitFork,
  CircleDot,
  MessagesSquare,
  ScrollText,
  Star,
} from "lucide-react";
import { useParams } from "next/navigation";
import { useState } from "react";

export default function ProjectPage() {
  const params = useParams<{ owner: string; name: string }>();
  const { owner, name } = params;
  const fullName = `${owner}/${name}`;
  const qc = useQueryClient();
  const [tab, setTab] = useState<"devlogs" | "chat">("devlogs");
  const { data: repo, isLoading, isError } = useRepo(owner, name);
  const postsQuery = useProjectPosts(fullName);
  const posts = postsQuery.data?.pages.flatMap((p) => p.results) ?? [];

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
        <div className="mb-4 flex gap-1 border-b border-border-strong">
          <TabButton
            active={tab === "devlogs"}
            onClick={() => setTab("devlogs")}
            icon={<ScrollText className="h-4 w-4" />}
            label="Devlogs"
          />
          <TabButton
            active={tab === "chat"}
            onClick={() => setTab("chat")}
            icon={<MessagesSquare className="h-4 w-4" />}
            label="Chat"
          />
        </div>

        {tab === "devlogs" ? (
          <>
            <div className="mb-4">
              <Composer
                pinnedRepo={repo}
                onPosted={() =>
                  qc.invalidateQueries({ queryKey: keys.projectPosts(fullName) })
                }
              />
            </div>

            <div className="space-y-4">
              {posts.length > 0 ? (
                <>
                  {posts.map((post) => (
                    <PostCard key={post.id} post={post} />
                  ))}
                  <LoadMore
                    hasNextPage={postsQuery.hasNextPage}
                    isFetchingNextPage={postsQuery.isFetchingNextPage}
                    fetchNextPage={postsQuery.fetchNextPage}
                  />
                </>
              ) : (
                <EmptyState
                  title="No devlogs yet"
                  description="Be the first to post an update about this project."
                />
              )}
            </div>
          </>
        ) : (
          <ChatPanel owner={repo.owner_login} name={repo.name} />
        )}
      </div>
    </div>
  );
}

function TabButton({
  active,
  onClick,
  icon,
  label,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "-mb-px flex items-center gap-1.5 border-b-2 px-3 py-2 text-sm font-medium transition-colors",
        active
          ? "border-accent text-fg"
          : "border-transparent text-muted hover:text-fg",
      )}
    >
      {icon}
      {label}
    </button>
  );
}
