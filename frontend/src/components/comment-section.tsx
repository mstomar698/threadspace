"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/card";
import { LoadMore } from "@/components/load-more";
import { useAddComment, useComments, useReplies } from "@/lib/queries";
import type { Comment } from "@/lib/types";
import { timeAgo } from "@/lib/utils";
import { MessageSquare } from "lucide-react";
import { useState } from "react";
import { Avatar } from "./ui/avatar";

export function CommentSection({ postId }: { postId: string }) {
  const { data, isLoading, hasNextPage, isFetchingNextPage, fetchNextPage } =
    useComments(postId);
  const addComment = useAddComment(postId);
  const [body, setBody] = useState("");
  const comments = data?.pages.flatMap((p) => p.results) ?? [];

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!body.trim()) return;
    await addComment.mutateAsync({ body: body.trim() });
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
          {comments.map((c) => (
            <CommentItem key={c.id} comment={c} postId={postId} />
          ))}
          {comments.length === 0 && (
            <p className="py-2 text-center text-sm text-faint">No comments yet.</p>
          )}
          <LoadMore
            hasNextPage={hasNextPage}
            isFetchingNextPage={isFetchingNextPage}
            fetchNextPage={fetchNextPage}
          />
        </ul>
      )}
    </div>
  );
}

/** A row showing one comment's body + author, with a Slack-style thread of
 * replies that expands on demand. */
function CommentRow({ comment }: { comment: Comment }) {
  return (
    <div className="flex gap-2.5">
      <Avatar
        src={comment.author.profileimg}
        username={comment.author.username}
        size={28}
      />
      <div className="min-w-0">
        <p className="text-sm">
          <span className="font-medium">{comment.author.username}</span>{" "}
          <span className="text-xs text-faint">{timeAgo(comment.created_at)}</span>
        </p>
        <p className="text-sm text-muted">{comment.body}</p>
      </div>
    </div>
  );
}

function CommentItem({
  comment,
  postId,
}: {
  comment: Comment;
  postId: string;
}) {
  const [open, setOpen] = useState(false);
  const [replying, setReplying] = useState(false);
  const [body, setBody] = useState("");
  const addReply = useAddComment(postId);
  const repliesQuery = useReplies(comment.id, open);
  const replies = repliesQuery.data?.pages.flatMap((p) => p.results) ?? [];

  async function submitReply(e: React.FormEvent) {
    e.preventDefault();
    if (!body.trim()) return;
    await addReply.mutateAsync({ body: body.trim(), parent: comment.id });
    setBody("");
    setReplying(false);
    setOpen(true); // reveal the thread so the new reply is visible
  }

  return (
    <li>
      <CommentRow comment={comment} />

      <div className="ml-[38px] mt-1 flex items-center gap-3 text-xs text-faint">
        <button
          type="button"
          onClick={() => setReplying((v) => !v)}
          className="hover:text-fg"
        >
          Reply
        </button>
        {comment.replies_count > 0 && (
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            className="flex items-center gap-1 hover:text-accent"
          >
            <MessageSquare className="h-3 w-3" />
            {open
              ? "Hide replies"
              : `${comment.replies_count} ${
                  comment.replies_count === 1 ? "reply" : "replies"
                }`}
          </button>
        )}
      </div>

      {replying && (
        <form onSubmit={submitReply} className="ml-[38px] mt-2 flex gap-2">
          <Input
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder={`Reply to ${comment.author.username}…`}
            className="h-8"
            autoFocus
          />
          <Button size="sm" type="submit" loading={addReply.isPending}>
            Send
          </Button>
        </form>
      )}

      {open && (
        <div className="ml-[38px] mt-2 space-y-3 border-l border-border-strong pl-3">
          {repliesQuery.isLoading ? (
            <div className="py-2">
              <Spinner className="h-4 w-4" />
            </div>
          ) : (
            <>
              {replies.map((r) => (
                <CommentRow key={r.id} comment={r} />
              ))}
              <LoadMore
                hasNextPage={repliesQuery.hasNextPage}
                isFetchingNextPage={repliesQuery.isFetchingNextPage}
                fetchNextPage={repliesQuery.fetchNextPage}
                label="More replies"
              />
            </>
          )}
        </div>
      )}
    </li>
  );
}
