"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { LiveEvent } from "./types";

const REALTIME_URL = process.env.NEXT_PUBLIC_REALTIME_URL;

/**
 * Subscribes to the Rust realtime gateway and counts incoming activity events
 * (posts from people you follow, GitHub releases/pushes). Reconnects with
 * exponential backoff. No-op when NEXT_PUBLIC_REALTIME_URL is unset.
 */
export function useLiveFeed(
  username: string | undefined,
  onEvent?: (event: LiveEvent) => void,
) {
  const [pending, setPending] = useState(0);
  const [connected, setConnected] = useState(false);
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  useEffect(() => {
    if (!REALTIME_URL || !username) return;

    let socket: WebSocket | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;
    let attempts = 0;
    let cancelled = false;

    const connect = () => {
      socket = new WebSocket(
        `${REALTIME_URL}/ws?user=${encodeURIComponent(username)}`,
      );

      socket.onopen = () => {
        attempts = 0;
        setConnected(true);
      };

      socket.onmessage = (message) => {
        try {
          const data = JSON.parse(message.data) as LiveEvent;
          if (data.type === "connected") return;
          // Don't nudge the user about their own posts.
          if (data.type === "post.created" && data.actor === username) return;
          setPending((count) => count + 1);
          onEventRef.current?.(data);
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
  }, [username]);

  const reset = useCallback(() => setPending(0), []);

  return { pending, connected, reset };
}
