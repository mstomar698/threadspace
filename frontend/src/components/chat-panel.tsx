"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/card";
import { LoadMore } from "@/components/load-more";
import { useChatHistory, useSendChat } from "@/lib/queries";
import type { LiveEvent } from "@/lib/types";
import { useChatRoom } from "@/lib/use-chat-room";
import { timeAgo } from "@/lib/utils";
import { useAuth } from "@/providers/auth-provider";
import { useCallback, useState } from "react";
import { Avatar } from "./ui/avatar";

interface ChatRow {
  key: string;
  username: string;
  profileimg: string | null;
  body: string;
  created_at: string;
}

export function ChatPanel({ owner, name }: { owner: string; name: string }) {
  const fullName = `${owner}/${name}`;
  const { profile } = useAuth();
  const me = profile?.username;
  const history = useChatHistory(owner, name);
  const send = useSendChat(owner, name);
  const [draft, setDraft] = useState("");
  // Messages received live from other users since the last history refetch.
  const [live, setLive] = useState<ChatRow[]>([]);

  const onMessage = useCallback(
    (event: LiveEvent) => {
      // The sender's own message arrives via the send mutation's refetch, so
      // skip the echo to avoid showing it twice.
      if (!event.actor || event.actor === me) return;
      setLive((rows) => [
        ...rows,
        {
          key: `live-${event.created_at}-${event.actor}-${rows.length}`,
          username: event.actor,
          profileimg: null,
          body: event.title ?? "",
          created_at: event.created_at ?? new Date().toISOString(),
        },
      ]);
    },
    [me],
  );

  const { connected } = useChatRoom(fullName, me, onMessage);

  // History pages come newest-first; flatten and flip to chronological order.
  const historyRows: ChatRow[] = (history.data?.pages.flatMap((p) => p.results) ?? [])
    .map((m) => ({
      key: `msg-${m.id}`,
      username: m.author.username,
      profileimg: m.author.profileimg,
      body: m.body,
      created_at: m.created_at,
    }))
    .reverse();

  const rows = [...historyRows, ...live];

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!draft.trim()) return;
    await send.mutateAsync(draft.trim());
    setDraft("");
    // Refetched history now includes everyone's messages, so reset the live buffer.
    setLive([]);
  }

  return (
    <div className="rounded-xl border border-border-strong bg-surface">
      <div className="flex items-center justify-between border-b border-border-strong px-4 py-2.5">
        <h3 className="text-sm font-semibold">Project chat</h3>
        <span className="flex items-center gap-1.5 text-xs text-faint">
          <span
            className={`h-2 w-2 rounded-full ${connected ? "bg-emerald-500" : "bg-faint"}`}
          />
          {connected ? "Live" : "Offline"}
        </span>
      </div>

      <div className="max-h-[28rem] space-y-3 overflow-y-auto px-4 py-3">
        <LoadMore
          hasNextPage={history.hasNextPage}
          isFetchingNextPage={history.isFetchingNextPage}
          fetchNextPage={history.fetchNextPage}
          label="Load earlier messages"
        />
        {history.isLoading ? (
          <div className="flex justify-center py-6">
            <Spinner />
          </div>
        ) : rows.length === 0 ? (
          <p className="py-6 text-center text-sm text-faint">
            No messages yet. Say hello 👋
          </p>
        ) : (
          rows.map((r) => (
            <div key={r.key} className="flex gap-2.5">
              <Avatar src={r.profileimg} username={r.username} size={28} />
              <div className="min-w-0">
                <p className="text-sm">
                  <span className="font-medium">{r.username}</span>{" "}
                  <span className="text-xs text-faint">{timeAgo(r.created_at)}</span>
                </p>
                <p className="whitespace-pre-wrap break-words text-sm text-muted">
                  {r.body}
                </p>
              </div>
            </div>
          ))
        )}
      </div>

      <form
        onSubmit={submit}
        className="flex gap-2 border-t border-border-strong px-4 py-3"
      >
        <Input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder={`Message #${name}…`}
          className="h-9"
        />
        <Button size="sm" type="submit" loading={send.isPending}>
          Send
        </Button>
      </form>
    </div>
  );
}
