"use client";

import { Card } from "@/components/ui/card";
import { useToggleLike } from "@/lib/queries";
import type { Post } from "@/lib/types";
import { cn, timeAgo } from "@/lib/utils";
import { Heart, MessageCircle } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Avatar } from "./ui/avatar";
import { CommentSection } from "./comment-section";

export function PostCard({ post }: { post: Post }) {
  const toggleLike = useToggleLike();
  const [showComments, setShowComments] = useState(false);

  // Optimistic-ish local view of like state for snappy UI.
  const [liked, setLiked] = useState(post.liked);
  const [likes, setLikes] = useState(post.num_likes);

  function onLike() {
    setLiked((v) => !v);
    setLikes((n) => n + (liked ? -1 : 1));
    toggleLike.mutate(post.id);
  }

  return (
    <Card className="overflow-hidden">
      <div className="flex items-center gap-3 px-4 py-3">
        <Avatar src={post.author.profileimg} username={post.author.username} size={40} />
        <div className="min-w-0">
          <Link
            href={`/${post.author.username}`}
            className="font-medium hover:underline"
          >
            {post.author.username}
          </Link>
          <p className="text-xs text-faint">{timeAgo(post.created_at)} ago</p>
        </div>
      </div>

      {post.caption && (
        <p className="whitespace-pre-wrap px-4 pb-3 text-[15px] leading-relaxed">
          {post.caption}
        </p>
      )}

      {post.image && (
        <div className="border-y border-border-strong bg-bg">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={post.image}
            alt={post.caption || "post"}
            className="max-h-[32rem] w-full object-cover"
          />
        </div>
      )}

      <div className="flex items-center gap-1 px-2 py-2">
        <button
          onClick={onLike}
          className={cn(
            "flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
            liked ? "text-danger" : "text-muted hover:bg-surface-2 hover:text-fg",
          )}
        >
          <Heart className={cn("h-5 w-5", liked && "fill-current")} />
          {likes}
        </button>
        <button
          onClick={() => setShowComments((v) => !v)}
          className={cn(
            "flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
            showComments ? "text-accent" : "text-muted hover:bg-surface-2 hover:text-fg",
          )}
        >
          <MessageCircle className="h-5 w-5" />
          {post.comments_count}
        </button>
      </div>

      {showComments && <CommentSection postId={post.id} />}
    </Card>
  );
}
