"use client";

import { Composer } from "@/components/composer";
import { ExploreResults } from "@/components/explore-results";
import { PostCard } from "@/components/post-card";
import { Button } from "@/components/ui/button";
import { EmptyState, Spinner } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { keys, useFeed } from "@/lib/queries";
import { useLiveFeed } from "@/lib/use-live-feed";
import { useAuth } from "@/providers/auth-provider";
import { useQueryClient } from "@tanstack/react-query";
import { ArrowUp, Rss, Search } from "lucide-react";
import { useEffect, useState } from "react";

export default function FeedPage() {
  const { profile } = useAuth();
  const qc = useQueryClient();
  const { data, isLoading, fetchNextPage, hasNextPage, isFetchingNextPage } =
    useFeed();
  const { pending, reset } = useLiveFeed(profile?.username);

  // Explore search lives on the feed page. Empty → the ranked feed; typing →
  // tabbed results (posts, users, projects, mentions). Debounced.
  const [q, setQ] = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  useEffect(() => {
    const id = setTimeout(() => setDebouncedQ(q.trim()), 300);
    return () => clearTimeout(id);
  }, [q]);
  const exploring = debouncedQ.length > 0;

  const posts = data?.pages.flatMap((p) => p.results) ?? [];

  const loadNew = () => {
    qc.invalidateQueries({ queryKey: keys.feed });
    reset();
  };

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">
          {exploring ? "Explore" : "Feed"}
        </h1>
        <p className="text-sm text-muted">
          {exploring
            ? "Search posts, people, projects, and mentions."
            : "Trending builds from people you follow — freshest and most active first."}
        </p>
      </div>

      <div className="relative">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-faint" />
        <Input
          className="pl-9"
          placeholder="Search posts, people, projects, @mentions…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
      </div>

      {exploring ? (
        <ExploreResults q={debouncedQ} />
      ) : (
        <>
          <Composer />

          {pending > 0 && (
            <div className="sticky top-2 z-10 flex justify-center">
              <Button size="sm" onClick={loadNew} className="shadow-lg">
                <ArrowUp className="h-4 w-4" />
                {pending} new {pending === 1 ? "update" : "updates"}
              </Button>
            </div>
          )}

          {isLoading ? (
            <div className="flex justify-center py-16">
              <Spinner />
            </div>
          ) : posts.length === 0 ? (
            <EmptyState
              icon={<Rss className="h-8 w-8" />}
              title="Your feed is quiet"
              description="Search above to find makers to follow, or share your first build."
            />
          ) : (
            <div className="space-y-4">
              {posts.map((post) => (
                <PostCard key={post.id} post={post} />
              ))}

              {hasNextPage && (
                <div className="flex justify-center pt-2">
                  <Button
                    variant="secondary"
                    onClick={() => fetchNextPage()}
                    loading={isFetchingNextPage}
                  >
                    Load more
                  </Button>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
