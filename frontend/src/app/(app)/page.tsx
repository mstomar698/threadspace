"use client";

import { Composer } from "@/components/composer";
import { PostCard } from "@/components/post-card";
import { Button } from "@/components/ui/button";
import { EmptyState, Spinner } from "@/components/ui/card";
import { keys, useFeed } from "@/lib/queries";
import { useLiveFeed } from "@/lib/use-live-feed";
import { useAuth } from "@/providers/auth-provider";
import { useQueryClient } from "@tanstack/react-query";
import { ArrowUp, Rss } from "lucide-react";

export default function FeedPage() {
  const { profile } = useAuth();
  const qc = useQueryClient();
  const { data, isLoading, fetchNextPage, hasNextPage, isFetchingNextPage } =
    useFeed();
  const { pending, reset } = useLiveFeed(profile?.username);

  const posts = data?.pages.flatMap((p) => p.results) ?? [];

  const loadNew = () => {
    qc.invalidateQueries({ queryKey: keys.feed });
    reset();
  };

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Feed</h1>
        <p className="text-sm text-muted">
          Latest from people you follow — and fresh builds to discover.
        </p>
      </div>

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
          description="Follow some makers from Explore, or share your first build above."
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
    </div>
  );
}
