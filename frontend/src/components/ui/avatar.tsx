"use client";

import { cn } from "@/lib/utils";
import { useState } from "react";

interface AvatarProps {
  src?: string | null;
  username: string;
  size?: number;
  className?: string;
}

function colorFor(username: string): string {
  const palette = ["#7c5cff", "#3fb950", "#d29922", "#f85149", "#1f9cf0", "#db61a2"];
  let hash = 0;
  for (let i = 0; i < username.length; i++) hash = username.charCodeAt(i) + ((hash << 5) - hash);
  return palette[Math.abs(hash) % palette.length];
}

export function Avatar({ src, username, size = 40, className }: AvatarProps) {
  const [errored, setErrored] = useState(false);
  const showImage = src && !errored;

  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center justify-center overflow-hidden rounded-full font-semibold text-white uppercase",
        className,
      )}
      style={{
        width: size,
        height: size,
        backgroundColor: showImage ? "transparent" : colorFor(username),
        fontSize: size * 0.4,
      }}
    >
      {showImage ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={src}
          alt={username}
          width={size}
          height={size}
          className="h-full w-full object-cover"
          onError={() => setErrored(true)}
        />
      ) : (
        username.charAt(0)
      )}
    </span>
  );
}
