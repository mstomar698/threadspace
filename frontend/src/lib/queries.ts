import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { api } from "./api";
import type {
  ChatMessage,
  Comment,
  CursorPaginated,
  GitHubAccountStatus,
  GithubLoginResult,
  Paginated,
  Post,
  Profile,
  Repo,
  RepoSuggestion,
} from "./types";

export const keys = {
  feed: ["feed"] as const,
  profile: (username: string) => ["profile", username] as const,
  comments: (postId: string) => ["comments", postId] as const,
  replies: (parentId: number) => ["replies", parentId] as const,
  search: (q: string) => ["search", q] as const,
  repo: (fullName: string) => ["repo", fullName] as const,
  projectPosts: (fullName: string) => ["project-posts", fullName] as const,
  chat: (fullName: string) => ["chat", fullName] as const,
  githubAccount: ["github-account"] as const,
};

export function useFeed() {
  return useInfiniteQuery({
    queryKey: keys.feed,
    queryFn: ({ pageParam }) =>
      api.get<CursorPaginated<Post>>(pageParam ?? "/posts/feed/"),
    initialPageParam: null as string | null,
    getNextPageParam: (last) => last.next,
  });
}

export function useProfile(username: string) {
  return useQuery({
    queryKey: keys.profile(username),
    queryFn: () => api.get<Profile>(`/profiles/${username}/`),
    enabled: !!username,
  });
}

export function useProfilePosts(username: string) {
  return useInfiniteQuery({
    queryKey: ["profile-posts", username],
    queryFn: ({ pageParam }) =>
      api.get<Paginated<Post>>(
        pageParam ?? `/posts/?author=${encodeURIComponent(username)}`,
      ),
    initialPageParam: null as string | null,
    getNextPageParam: (last) => last.next,
    enabled: !!username,
  });
}

export function useSearch(q: string) {
  return useInfiniteQuery({
    queryKey: keys.search(q),
    queryFn: ({ pageParam }) =>
      api.get<Paginated<Profile>>(
        pageParam ?? `/profiles/?search=${encodeURIComponent(q)}`,
      ),
    initialPageParam: null as string | null,
    getNextPageParam: (last) => last.next,
    enabled: q.trim().length > 0,
  });
}

export function useComments(postId: string) {
  return useInfiniteQuery({
    queryKey: keys.comments(postId),
    queryFn: ({ pageParam }) =>
      api.get<Paginated<Comment>>(pageParam ?? `/comments/?post=${postId}`),
    initialPageParam: null as string | null,
    getNextPageParam: (last) => last.next,
    enabled: !!postId,
  });
}

/** Replies within a thread (one level deep). Disabled until the thread opens. */
export function useReplies(parentId: number, enabled: boolean) {
  return useInfiniteQuery({
    queryKey: keys.replies(parentId),
    queryFn: ({ pageParam }) =>
      api.get<Paginated<Comment>>(pageParam ?? `/comments/?parent=${parentId}`),
    initialPageParam: null as string | null,
    getNextPageParam: (last) => last.next,
    enabled: enabled && !!parentId,
  });
}

export function useCreatePost() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (form: FormData) => api.postForm<Post>("/posts/", form),
    onSuccess: () => {
      // A new post should surface everywhere it could appear, overriding the
      // 30s staleTime so the author's profile and the project's devlogs refetch.
      qc.invalidateQueries({ queryKey: keys.feed });
      qc.invalidateQueries({ queryKey: ["profile-posts"] });
      qc.invalidateQueries({ queryKey: ["project-posts"] });
    },
  });
}

export function useResolveRepo() {
  return useMutation({
    mutationFn: (q: string) => api.post<Repo>("/github/resolve/", { q }),
  });
}

/** Autofill suggestions from the cached repo catalogue (debounce the input). */
export function useRepoSuggest(q: string) {
  return useQuery({
    queryKey: ["repo-suggest", q],
    queryFn: () =>
      api.get<RepoSuggestion[]>(
        `/github/repos/suggest/?q=${encodeURIComponent(q)}`,
      ),
    enabled: q.trim().length > 0,
  });
}

export function useRepo(owner: string, name: string) {
  return useQuery({
    queryKey: keys.repo(`${owner}/${name}`),
    queryFn: () => api.get<Repo>(`/github/repos/${owner}/${name}/`),
    enabled: !!owner && !!name,
  });
}

/** The current user's imported repositories. */
export function useMyRepos() {
  return useInfiniteQuery({
    queryKey: ["repos", "mine"],
    queryFn: ({ pageParam }) =>
      api.get<Paginated<Repo>>(pageParam ?? "/github/repos/?mine=1"),
    initialPageParam: null as string | null,
    getNextPageParam: (last) => last.next,
  });
}

/** Repositories owned by a given GitHub login (for profile pages). */
export function useUserRepos(owner: string | null | undefined) {
  return useInfiniteQuery({
    queryKey: ["repos", "owner", owner],
    queryFn: ({ pageParam }) =>
      api.get<Paginated<Repo>>(
        pageParam ?? `/github/repos/?owner=${encodeURIComponent(owner ?? "")}`,
      ),
    initialPageParam: null as string | null,
    getNextPageParam: (last) => last.next,
    enabled: !!owner,
  });
}

/** Search across all cached projects. */
export function useRepoSearch(q: string) {
  return useInfiniteQuery({
    queryKey: ["repos", "search", q],
    queryFn: ({ pageParam }) =>
      api.get<Paginated<Repo>>(
        pageParam ?? `/github/repos/?search=${encodeURIComponent(q)}`,
      ),
    initialPageParam: null as string | null,
    getNextPageParam: (last) => last.next,
    enabled: q.trim().length > 0,
  });
}

export function useProjectPosts(fullName: string) {
  return useInfiniteQuery({
    queryKey: keys.projectPosts(fullName),
    queryFn: ({ pageParam }) =>
      api.get<Paginated<Post>>(
        pageParam ?? `/posts/?repo=${encodeURIComponent(fullName)}`,
      ),
    initialPageParam: null as string | null,
    getNextPageParam: (last) => last.next,
    enabled: !!fullName,
  });
}

/** Paginated chat history for a project room (newest page first). */
export function useChatHistory(owner: string, name: string) {
  const fullName = `${owner}/${name}`;
  return useInfiniteQuery({
    queryKey: keys.chat(fullName),
    queryFn: ({ pageParam }) =>
      api.get<Paginated<ChatMessage>>(
        pageParam ?? `/github/repos/${owner}/${name}/chat/`,
      ),
    initialPageParam: null as string | null,
    getNextPageParam: (last) => last.next,
    enabled: !!owner && !!name,
  });
}

/** Send a message to a project's chat room. */
export function useSendChat(owner: string, name: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: string) =>
      api.post<ChatMessage>(`/github/repos/${owner}/${name}/chat/`, { body }),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: keys.chat(`${owner}/${name}`) }),
  });
}

export function useGithubAccount() {
  return useQuery({
    queryKey: keys.githubAccount,
    queryFn: () => api.get<GitHubAccountStatus>("/github/account/"),
  });
}

export function useConnectGithub() {
  return useMutation({
    mutationFn: async () => {
      const { authorize_url } = await api.get<{ authorize_url: string }>(
        "/github/oauth/authorize-url/",
      );
      return authorize_url;
    },
  });
}

/** Start the "Sign in with GitHub" flow (works while logged out). */
export function useGithubLogin() {
  return useMutation({
    mutationFn: () =>
      api.get<{ authorize_url: string; nonce: string }>(
        "/github/oauth/login-url/",
        false,
      ),
  });
}

/** Complete GitHub sign-in: exchange the code (+ nonce) for ThreadSpace JWTs. */
export function useGithubLoginCallback() {
  return useMutation({
    mutationFn: (input: { code: string; state: string; nonce: string }) =>
      api.post<GithubLoginResult>("/github/oauth/login/", input, false),
  });
}

export function useGithubCallback() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { code: string; state: string }) =>
      api.post<GitHubAccountStatus>("/github/oauth/callback/", input),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.githubAccount }),
  });
}

export function useImportRepos() {
  return useMutation({
    mutationFn: () => api.post<Repo[]>("/github/import/"),
  });
}

export function useDisconnectGithub() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.delete("/github/account/"),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.githubAccount }),
  });
}

export function useToggleLike() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (postId: string) =>
      api.post<{ liked: boolean; num_likes: number }>(`/posts/${postId}/like/`),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.feed }),
  });
}

export function useToggleFollow(username: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<{ following: boolean }>(`/profiles/${username}/follow/`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.profile(username) });
      qc.invalidateQueries({ queryKey: keys.feed });
    },
  });
}

export function useAddComment(postId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { body: string; parent?: number }) =>
      api.post<Comment>("/comments/", {
        post: postId,
        body: input.body,
        ...(input.parent ? { parent: input.parent } : {}),
      }),
    onSuccess: (_data, input) => {
      // Refresh top-level comments (also updates each comment's replies_count).
      qc.invalidateQueries({ queryKey: keys.comments(postId) });
      if (input.parent) {
        qc.invalidateQueries({ queryKey: keys.replies(input.parent) });
      }
      qc.invalidateQueries({ queryKey: keys.feed });
    },
  });
}
