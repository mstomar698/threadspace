"use client";

import { PostCard } from "@/components/post-card";
import { Button } from "@/components/ui/button";
import { Avatar } from "@/components/ui/avatar";
import { EmptyState, Spinner } from "@/components/ui/card";
import { useProfile, useProfilePosts, useToggleFollow } from "@/lib/queries";
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
  const { profile: me } = useAuth();
  const { data: profile, isLoading } = useProfile(username);
  const { data: posts } = useProfilePosts(username);
  const toggleFollow = useToggleFollow(username);

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
                onClick={() => toggleFollow.mutate()}
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

      <div className="space-y-4">
        {posts && posts.results.length > 0 ? (
          posts.results.map((post) => <PostCard key={post.id} post={post} />)
        ) : (
          <EmptyState title="No posts yet" />
        )}
      </div>
    </div>
  );
}
