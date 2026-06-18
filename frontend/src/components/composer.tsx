"use client";

import { Button } from "@/components/ui/button";
import { Card, Spinner } from "@/components/ui/card";
import { Input, Textarea } from "@/components/ui/input";
import { errorMessage } from "@/lib/api";
import { useCreatePost, useRepoSuggest, useResolveRepo } from "@/lib/queries";
import type { Repo } from "@/lib/types";
import { useAuth } from "@/providers/auth-provider";
import { GitBranch, ImagePlus, Star, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
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
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [repo, setRepo] = useState<Repo | null>(pinnedRepo ?? null);
  const locked = !!pinnedRepo;
  const inputRef = useRef<HTMLInputElement>(null);

  // Debounce the autofill query so we hit the suggest endpoint ~3×/sec at most.
  useEffect(() => {
    const id = setTimeout(() => setDebouncedQuery(repoQuery.trim()), 250);
    return () => clearTimeout(id);
  }, [repoQuery]);
  const { data: suggestions } = useRepoSuggest(showRepoInput ? debouncedQuery : "");

  function pickFile(f: File | null) {
    setFile(f);
    setPreview(f ? URL.createObjectURL(f) : null);
  }

  // Resolve a repo reference (owner/name, URL, or a picked suggestion) to the
  // full cached Repo and attach it. DB-first: suggestions resolve instantly
  // from the cache; an unknown owner/name falls back to a live GitHub lookup.
  async function attachRepo(value?: string) {
    const q = (value ?? repoQuery).trim();
    if (!q) return;
    setError(null);
    try {
      const resolved = await resolveRepo.mutateAsync(q);
      setRepo(resolved);
      setShowRepoInput(false);
      setRepoQuery("");
      setDebouncedQuery("");
    } catch (err) {
      setError(errorMessage(err, "Could not find that repository"));
    }
  }

  async function submit() {
    setError(null);
    // A devlog can be text-only, repo-only, or include an image — but needs at
    // least one of the three.
    if (!file && !caption.trim() && !repo) {
      setError("Write something, attach a repo, or add an image.");
      return;
    }
    const form = new FormData();
    if (file) form.append("image", file);
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
            <div className="mt-2">
              <div className="flex gap-2">
                <Input
                  value={repoQuery}
                  onChange={(e) => setRepoQuery(e.target.value)}
                  placeholder="Search projects, or owner/name…"
                  className="h-9"
                  onKeyDown={(e) => e.key === "Enter" && attachRepo()}
                  autoFocus
                />
                <Button size="sm" onClick={() => attachRepo()} disabled={resolveRepo.isPending}>
                  {resolveRepo.isPending ? <Spinner className="h-4 w-4" /> : "Add"}
                </Button>
              </div>
              {suggestions && suggestions.length > 0 && (
                <ul className="mt-1 overflow-hidden rounded-lg border border-border-strong bg-surface">
                  {suggestions.map((s) => (
                    <li key={s.full_name}>
                      <button
                        type="button"
                        onClick={() => attachRepo(s.full_name)}
                        className="flex w-full items-center justify-between gap-3 px-3 py-2 text-left hover:bg-surface-2"
                      >
                        <span className="min-w-0">
                          <span className="font-mono text-sm">
                            {s.owner_login}/<span className="text-accent">{s.name}</span>
                          </span>
                          {s.description && (
                            <span className="block truncate text-xs text-muted">
                              {s.description}
                            </span>
                          )}
                        </span>
                        <span className="flex shrink-0 items-center gap-1 text-xs text-faint">
                          <Star className="h-3 w-3" />
                          {s.stargazers_count.toLocaleString()}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
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
