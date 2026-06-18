"use client";

import { PostCard } from "@/components/post-card";
import { RepoCard } from "@/components/repo-card";
import { LoadMore } from "@/components/load-more";
import { Button } from "@/components/ui/button";
import { Avatar } from "@/components/ui/avatar";
import { EmptyState, Spinner } from "@/components/ui/card";
import {
  useProfile,
  useProfilePosts,
  useToggleFollow,
  useUserRepos,
} from "@/lib/queries";
import { useAuth } from "@/providers/auth-provider";
import { MapPin } from "lucide-react";
import { useParams } from "next/navigation";

function Stat({ value, label }: { value: number; label: string }) {
  return (
    <div className="flex items-baseline gap-1.5">
      <span className="font-semibold text-fg">{value}</span>
      <span className="text-sm text-muted">{label}</span>
    </div>
  );
}

export default function ProfilePage() {
  const params = useParams<{ username: string }>();
  const username = params.username;
  const { profile: me, refresh } = useAuth();
  const { data: profile, isLoading } = useProfile(username);
  const postsQuery = useProfilePosts(username);
  const reposQuery = useUserRepos(profile?.github_login);
  const toggleFollow = useToggleFollow(username);

  const posts = postsQuery.data?.pages.flatMap((p) => p.results) ?? [];
  const repos = reposQuery.data?.pages.flatMap((p) => p.results) ?? [];

  if (isLoading || !profile) {
    return (
      <div className="flex justify-center py-16">
        <Spinner />
      </div>
    );
  }

  const isSelf = me?.username === profile.username;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
        <Avatar src={profile.profileimg} username={profile.username} size={84} />
        <div className="flex-1">
          <div className="flex items-center justify-between gap-3">
            <h1 className="text-2xl font-semibold tracking-tight">
              {profile.username}
            </h1>
            {!isSelf && (
              <Button
                variant={profile.is_following ? "secondary" : "primary"}
                onClick={() =>
                  toggleFollow.mutate(undefined, { onSuccess: () => refresh() })
                }
                loading={toggleFollow.isPending}
              >
                {profile.is_following ? "Following" : "Follow"}
              </Button>
            )}
          </div>

          {profile.bio && <p className="mt-2 text-sm text-fg/90">{profile.bio}</p>}
          {profile.location && (
            <p className="mt-1 flex items-center gap-1 text-sm text-muted">
              <MapPin className="h-3.5 w-3.5" />
              {profile.location}
            </p>
          )}

          <div className="mt-3 flex gap-5">
            <Stat value={profile.posts_count} label="posts" />
            <Stat value={profile.followers_count} label="followers" />
            <Stat value={profile.following_count} label="following" />
          </div>
        </div>
      </div>

      {repos.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-faint">
            Projects
          </h2>
          <div className="grid gap-3 sm:grid-cols-2">
            {repos.map((repo) => (
              <RepoCard key={repo.full_name} repo={repo} />
            ))}
          </div>
          <LoadMore
            hasNextPage={reposQuery.hasNextPage}
            isFetchingNextPage={reposQuery.isFetchingNextPage}
            fetchNextPage={reposQuery.fetchNextPage}
          />
        </section>
      )}

      <section className="space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-faint">
          Posts
        </h2>
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
          <EmptyState title="No posts yet" />
        )}
      </section>
    </div>
  );
}
