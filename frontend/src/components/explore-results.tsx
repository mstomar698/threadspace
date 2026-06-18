"use client";

import { PostCard } from "@/components/post-card";
import { RepoCard } from "@/components/repo-card";
import { LoadMore } from "@/components/load-more";
import { Avatar } from "@/components/ui/avatar";
import { Card, EmptyState, Spinner } from "@/components/ui/card";
import {
  useMentions,
  usePostSearch,
  useRepoSearch,
  useSearch,
} from "@/lib/queries";
import { cn } from "@/lib/utils";
import { AtSign, FolderGit2, Rss, Users } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

type Tab = "posts" | "users" | "projects" | "mentions";

const TABS: { key: Tab; label: string; icon: typeof Rss }[] = [
  { key: "posts", label: "Posts", icon: Rss },
  { key: "users", label: "Users", icon: Users },
  { key: "projects", label: "Projects", icon: FolderGit2 },
  { key: "mentions", label: "Mentions", icon: AtSign },
];

export function ExploreResults({ q }: { q: string }) {
  const [tab, setTab] = useState<Tab>("posts");

  // Only the active tab's query runs (others receive "" → disabled), so tab
  // switches are instant from cache without firing four searches per keystroke.
  const posts = usePostSearch(tab === "posts" ? q : "");
  const users = useSearch(tab === "users" ? q : "");
  const projects = useRepoSearch(tab === "projects" ? q : "");
  const mentions = useMentions(tab === "mentions" ? q : "");

  return (
    <div className="space-y-4">
      <div className="flex gap-1 overflow-x-auto border-b border-border-strong">
        {TABS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={cn(
              "-mb-px flex items-center gap-1.5 whitespace-nowrap border-b-2 px-3 py-2 text-sm font-medium transition-colors",
              tab === key
                ? "border-accent text-fg"
                : "border-transparent text-muted hover:text-fg",
            )}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </div>

      {tab === "posts" && (
        <PostResults query={posts} emptyLabel={`No posts match “${q}”.`} />
      )}
      {tab === "mentions" && (
        <PostResults query={mentions} emptyLabel={`No posts mention “${q}”.`} />
      )}
      {tab === "users" && <UserResults query={users} q={q} />}
      {tab === "projects" && <ProjectResults query={projects} q={q} />}
    </div>
  );
}

type Infinite<T> = {
  data?: { pages: { results: T[] }[] };
  isLoading: boolean;
  hasNextPage?: boolean;
  isFetchingNextPage: boolean;
  fetchNextPage: () => void;
};

function Loading() {
  return (
    <div className="flex justify-center py-12">
      <Spinner />
    </div>
  );
}

function PostResults({
  query,
  emptyLabel,
}: {
  query: Infinite<import("@/lib/types").Post>;
  emptyLabel: string;
}) {
  const posts = query.data?.pages.flatMap((p) => p.results) ?? [];
  if (query.isLoading) return <Loading />;
  if (posts.length === 0) return <EmptyState title="No results" description={emptyLabel} />;
  return (
    <div className="space-y-4">
      {posts.map((p) => (
        <PostCard key={p.id} post={p} />
      ))}
      <LoadMore
        hasNextPage={query.hasNextPage}
        isFetchingNextPage={query.isFetchingNextPage}
        fetchNextPage={query.fetchNextPage}
      />
    </div>
  );
}

function UserResults({
  query,
  q,
}: {
  query: Infinite<import("@/lib/types").Profile>;
  q: string;
}) {
  const users = query.data?.pages.flatMap((p) => p.results) ?? [];
  if (query.isLoading) return <Loading />;
  if (users.length === 0)
    return <EmptyState title="No results" description={`No users match “${q}”.`} />;
  return (
    <div className="space-y-2">
      {users.map((p) => (
        <Link key={p.username} href={`/${p.username}`}>
          <Card className="flex items-center gap-3 p-3 transition-colors hover:bg-surface-2">
            <Avatar src={p.profileimg} username={p.username} size={44} />
            <div className="min-w-0 flex-1">
              <p className="font-medium">{p.username}</p>
              <p className="truncate text-sm text-muted">
                {p.bio || `${p.followers_count} followers`}
              </p>
            </div>
          </Card>
        </Link>
      ))}
      <LoadMore
        hasNextPage={query.hasNextPage}
        isFetchingNextPage={query.isFetchingNextPage}
        fetchNextPage={query.fetchNextPage}
      />
    </div>
  );
}

function ProjectResults({
  query,
  q,
}: {
  query: Infinite<import("@/lib/types").Repo>;
  q: string;
}) {
  const repos = query.data?.pages.flatMap((p) => p.results) ?? [];
  if (query.isLoading) return <Loading />;
  if (repos.length === 0)
    return <EmptyState title="No results" description={`No projects match “${q}”.`} />;
  return (
    <div className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-2">
        {repos.map((r) => (
          <RepoCard key={r.full_name} repo={r} />
        ))}
      </div>
      <LoadMore
        hasNextPage={query.hasNextPage}
        isFetchingNextPage={query.isFetchingNextPage}
        fetchNextPage={query.fetchNextPage}
      />
    </div>
  );
}
