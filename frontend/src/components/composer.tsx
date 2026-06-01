"use client";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Textarea } from "@/components/ui/input";
import { errorMessage } from "@/lib/api";
import { useCreatePost } from "@/lib/queries";
import { useAuth } from "@/providers/auth-provider";
import { ImagePlus, X } from "lucide-react";
import { useRef, useState } from "react";
import { Avatar } from "./ui/avatar";

export function Composer() {
  const { profile } = useAuth();
  const createPost = useCreatePost();
  const [caption, setCaption] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  function pickFile(f: File | null) {
    setFile(f);
    setPreview(f ? URL.createObjectURL(f) : null);
  }

  async function submit() {
    setError(null);
    if (!file) {
      setError("Add an image to share your build.");
      return;
    }
    const form = new FormData();
    form.append("image", file);
    form.append("caption", caption);
    try {
      await createPost.mutateAsync(form);
      setCaption("");
      pickFile(null);
    } catch (err) {
      setError(errorMessage(err, "Could not post"));
    }
  }

  return (
    <Card className="p-4">
      <div className="flex gap-3">
        {profile && (
          <Avatar src={profile.profileimg} username={profile.username} size={40} />
        )}
        <div className="flex-1">
          <Textarea
            value={caption}
            onChange={(e) => setCaption(e.target.value)}
            placeholder="What did you ship today?"
            rows={2}
            className="border-0 bg-transparent px-0 focus:ring-0 text-base"
          />

          {preview && (
            <div className="relative mt-2 overflow-hidden rounded-lg border border-border-strong">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={preview} alt="preview" className="max-h-80 w-full object-cover" />
              <button
                onClick={() => pickFile(null)}
                className="absolute right-2 top-2 rounded-full bg-black/60 p-1.5 text-white hover:bg-black/80"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          )}

          {error && <p className="mt-2 text-sm text-danger">{error}</p>}

          <div className="mt-3 flex items-center justify-between border-t border-border-strong pt-3">
            <input
              ref={inputRef}
              type="file"
              accept="image/*"
              hidden
              onChange={(e) => pickFile(e.target.files?.[0] ?? null)}
            />
            <Button
              variant="ghost"
              size="sm"
              onClick={() => inputRef.current?.click()}
            >
              <ImagePlus className="h-4 w-4" />
              Image
            </Button>
            <Button size="sm" onClick={submit} loading={createPost.isPending}>
              Post
            </Button>
          </div>
        </div>
      </div>
    </Card>
  );
}
