"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/card";
import { useAddComment, useComments } from "@/lib/queries";
import { timeAgo } from "@/lib/utils";
import { useState } from "react";
import { Avatar } from "./ui/avatar";

export function CommentSection({ postId }: { postId: string }) {
  const { data, isLoading } = useComments(postId);
  const addComment = useAddComment(postId);
  const [body, setBody] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!body.trim()) return;
    await addComment.mutateAsync(body.trim());
    setBody("");
  }

  return (
    <div className="border-t border-border-strong px-4 py-3">
      <form onSubmit={submit} className="mb-3 flex gap-2">
        <Input
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="Add a comment..."
          className="h-9"
        />
        <Button size="sm" type="submit" loading={addComment.isPending}>
          Reply
        </Button>
      </form>

      {isLoading ? (
        <div className="flex justify-center py-4">
          <Spinner />
        </div>
      ) : (
        <ul className="space-y-3">
          {data?.results.map((c) => (
            <li key={c.id} className="flex gap-2.5">
              <Avatar src={c.author.profileimg} username={c.author.username} size={28} />
              <div className="min-w-0">
                <p className="text-sm">
                  <span className="font-medium">{c.author.username}</span>{" "}
                  <span className="text-xs text-faint">{timeAgo(c.created_at)}</span>
                </p>
                <p className="text-sm text-muted">{c.body}</p>
              </div>
            </li>
          ))}
          {data && data.results.length === 0 && (
            <p className="py-2 text-center text-sm text-faint">No comments yet.</p>
          )}
        </ul>
      )}
    </div>
  );
}
