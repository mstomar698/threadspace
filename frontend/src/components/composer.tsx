"use client";

import { Button } from "@/components/ui/button";
import { Card, Spinner } from "@/components/ui/card";
import { Input, Textarea } from "@/components/ui/input";
import { errorMessage } from "@/lib/api";
import { useCreatePost, useResolveRepo } from "@/lib/queries";
import type { Repo } from "@/lib/types";
import { useAuth } from "@/providers/auth-provider";
import { GitBranch, ImagePlus, X } from "lucide-react";
import { useRef, useState } from "react";
import { Avatar } from "./ui/avatar";
import { RepoCard } from "./repo-card";

export function Composer({
  pinnedRepo,
  onPosted,
}: {
  /** When set, the post is locked to this repo (e.g. on a project page). */
  pinnedRepo?: Repo;
  /** Called after a post is created (e.g. to refresh that project's devlogs). */
  onPosted?: () => void;
} = {}) {
  const { profile } = useAuth();
  const createPost = useCreatePost();
  const resolveRepo = useResolveRepo();
  const [caption, setCaption] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showRepoInput, setShowRepoInput] = useState(false);
  const [repoQuery, setRepoQuery] = useState("");
  const [repo, setRepo] = useState<Repo | null>(pinnedRepo ?? null);
  const locked = !!pinnedRepo;
  const inputRef = useRef<HTMLInputElement>(null);

  function pickFile(f: File | null) {
    setFile(f);
    setPreview(f ? URL.createObjectURL(f) : null);
  }

  async function attachRepo() {
    if (!repoQuery.trim()) return;
    setError(null);
    try {
      const resolved = await resolveRepo.mutateAsync(repoQuery.trim());
      setRepo(resolved);
      setShowRepoInput(false);
      setRepoQuery("");
    } catch (err) {
      setError(errorMessage(err, "Could not find that repository"));
    }
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
    if (repo) form.append("repo_full_name", repo.full_name);
    try {
      await createPost.mutateAsync(form);
      setCaption("");
      pickFile(null);
      setRepo(pinnedRepo ?? null);
      onPosted?.();
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
            placeholder={
              pinnedRepo ? `Share an update on ${pinnedRepo.name}…` : "What did you ship today?"
            }
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

          {repo && (
            <div className="relative mt-2">
              <RepoCard repo={repo} linkToProject={false} />
              {!locked && (
                <button
                  onClick={() => setRepo(null)}
                  className="absolute right-2 top-2 rounded-full bg-black/50 p-1 text-white hover:bg-black/70"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
          )}

          {showRepoInput && (
            <div className="mt-2 flex gap-2">
              <Input
                value={repoQuery}
                onChange={(e) => setRepoQuery(e.target.value)}
                placeholder="owner/name or GitHub URL"
                className="h-9"
                onKeyDown={(e) => e.key === "Enter" && attachRepo()}
                autoFocus
              />
              <Button size="sm" onClick={attachRepo} disabled={resolveRepo.isPending}>
                {resolveRepo.isPending ? <Spinner className="h-4 w-4" /> : "Add"}
              </Button>
            </div>
          )}

          {error && <p className="mt-2 text-sm text-danger">{error}</p>}

          <div className="mt-3 flex items-center justify-between border-t border-border-strong pt-3">
            <div className="flex items-center gap-1">
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
              {!locked && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowRepoInput((v) => !v)}
                >
                  <GitBranch className="h-4 w-4" />
                  Repo
                </Button>
              )}
            </div>
            <Button size="sm" onClick={submit} loading={createPost.isPending}>
              Post
            </Button>
          </div>
        </div>
      </div>
    </Card>
  );
}
