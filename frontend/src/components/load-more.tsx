"use client";

import { Button } from "@/components/ui/button";

/** A centered "Load more" button for infinite-query lists. Renders nothing when
 * there are no more pages to fetch. */
export function LoadMore({
  hasNextPage,
  isFetchingNextPage,
  fetchNextPage,
  label = "Load more",
}: {
  hasNextPage: boolean | undefined;
  isFetchingNextPage: boolean;
  fetchNextPage: () => void;
  label?: string;
}) {
  if (!hasNextPage) return null;
  return (
    <div className="flex justify-center pt-2">
      <Button
        variant="secondary"
        onClick={() => fetchNextPage()}
        loading={isFetchingNextPage}
      >
        {label}
      </Button>
    </div>
  );
}
