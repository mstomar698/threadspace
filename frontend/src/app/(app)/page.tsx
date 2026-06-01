"use client";

import { Composer } from "@/components/composer";
import { PostCard } from "@/components/post-card";
import { Button } from "@/components/ui/button";
import { EmptyState, Spinner } from "@/components/ui/card";
import { useFeed } from "@/lib/queries";
import { Rss } from "lucide-react";

export default function FeedPage() {
  const { data, isLoading, fetchNextPage, hasNextPage, isFetchingNextPage } =
    useFeed();

  const posts = data?.pages.flatMap((p) => p.results) ?? [];

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Feed</h1>
        <p className="text-sm text-muted">Latest from people you follow.</p>
      </div>

      <Composer />

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
