"use client";

import { useEffect, useRef, useState } from "react";
import type { LiveEvent } from "./types";

const REALTIME_URL = process.env.NEXT_PUBLIC_REALTIME_URL;

/**
 * Subscribes to a project's chat room on the Rust realtime gateway and invokes
 * `onMessage` for every `chat.message` event in that room. Reconnects with
 * exponential backoff. No-op (returns `connected: false`) when
 * NEXT_PUBLIC_REALTIME_URL is unset — history still works over REST.
 */
export function useChatRoom(
  room: string,
  username: string | undefined,
  onMessage: (event: LiveEvent) => void,
) {
  const [connected, setConnected] = useState(false);
  const onMessageRef = useRef(onMessage);

  useEffect(() => {
    onMessageRef.current = onMessage;
  });

  useEffect(() => {
    if (!REALTIME_URL || !room) return;

    let socket: WebSocket | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;
    let attempts = 0;
    let cancelled = false;

    const connect = () => {
      const params = new URLSearchParams({ room });
      if (username) params.set("user", username);
      socket = new WebSocket(`${REALTIME_URL}/ws?${params.toString()}`);

      socket.onopen = () => {
        attempts = 0;
        setConnected(true);
      };

      socket.onmessage = (message) => {
        try {
          const data = JSON.parse(message.data) as LiveEvent;
          if (data.type === "chat.message") onMessageRef.current?.(data);
        } catch {
          /* ignore malformed frames */
        }
      };

      socket.onclose = () => {
        setConnected(false);
        if (cancelled) return;
        attempts += 1;
        const delay = Math.min(1000 * 2 ** attempts, 15000);
        retryTimer = setTimeout(connect, delay);
      };

      socket.onerror = () => socket?.close();
    };

    connect();

    return () => {
      cancelled = true;
      if (retryTimer) clearTimeout(retryTimer);
      socket?.close();
    };
  }, [room, username]);

  return { connected };
}
