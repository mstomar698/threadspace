"use client";

import { Avatar } from "@/components/ui/avatar";
import { Card, EmptyState, Spinner } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { LoadMore } from "@/components/load-more";
import { useSearch } from "@/lib/queries";
import { Search as SearchIcon } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

export default function SearchPage() {
  const [q, setQ] = useState("");
  const {
    data,
    isLoading,
    isFetching,
    hasNextPage,
    isFetchingNextPage,
    fetchNextPage,
  } = useSearch(q);
  const results = data?.pages.flatMap((p) => p.results) ?? [];

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Explore</h1>
        <p className="text-sm text-muted">Find makers to follow.</p>
      </div>

      <div className="relative">
        <SearchIcon className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-faint" />
        <Input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search by username..."
          className="pl-9"
          autoFocus
        />
      </div>

      {q.trim() === "" ? (
        <EmptyState
          icon={<SearchIcon className="h-8 w-8" />}
          title="Search ThreadSpace"
          description="Type a username to discover developers."
        />
      ) : isLoading || (isFetching && results.length === 0) ? (
        <div className="flex justify-center py-12">
          <Spinner />
        </div>
      ) : results.length > 0 ? (
        <div className="space-y-2">
          {results.map((p) => (
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
            hasNextPage={hasNextPage}
            isFetchingNextPage={isFetchingNextPage}
            fetchNextPage={fetchNextPage}
          />
        </div>
      ) : (
        <EmptyState title="No results" description={`No users match "${q}".`} />
      )}
    </div>
  );
}
