import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { api } from "./api";
import type {
  Comment,
  CursorPaginated,
  GitHubAccountStatus,
  GithubLoginResult,
  Paginated,
  Post,
  Profile,
  Repo,
} from "./types";

export const keys = {
  feed: ["feed"] as const,
  profile: (username: string) => ["profile", username] as const,
  comments: (postId: string) => ["comments", postId] as const,
  search: (q: string) => ["search", q] as const,
  repo: (fullName: string) => ["repo", fullName] as const,
  projectPosts: (fullName: string) => ["project-posts", fullName] as const,
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
  return useQuery({
    queryKey: ["profile-posts", username],
    queryFn: () =>
      api.get<Paginated<Post>>(`/posts/?author=${encodeURIComponent(username)}`),
    enabled: !!username,
  });
}

export function useSearch(q: string) {
  return useQuery({
    queryKey: keys.search(q),
    queryFn: () =>
      api.get<Paginated<Profile>>(`/profiles/?search=${encodeURIComponent(q)}`),
    enabled: q.trim().length > 0,
  });
}

export function useComments(postId: string) {
  return useQuery({
    queryKey: keys.comments(postId),
    queryFn: () => api.get<Paginated<Comment>>(`/comments/?post=${postId}`),
    enabled: !!postId,
  });
}

export function useCreatePost() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (form: FormData) => api.postForm<Post>("/posts/", form),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.feed }),
  });
}

export function useResolveRepo() {
  return useMutation({
    mutationFn: (q: string) => api.post<Repo>("/github/resolve/", { q }),
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
  return useQuery({
    queryKey: ["repos", "mine"],
    queryFn: () => api.get<Paginated<Repo>>("/github/repos/?mine=1"),
  });
}

/** Repositories owned by a given GitHub login (for profile pages). */
export function useUserRepos(owner: string | null | undefined) {
  return useQuery({
    queryKey: ["repos", "owner", owner],
    queryFn: () =>
      api.get<Paginated<Repo>>(`/github/repos/?owner=${encodeURIComponent(owner ?? "")}`),
    enabled: !!owner,
  });
}

/** Search across all cached projects. */
export function useRepoSearch(q: string) {
  return useQuery({
    queryKey: ["repos", "search", q],
    queryFn: () =>
      api.get<Paginated<Repo>>(`/github/repos/?search=${encodeURIComponent(q)}`),
    enabled: q.trim().length > 0,
  });
}

export function useProjectPosts(fullName: string) {
  return useQuery({
    queryKey: keys.projectPosts(fullName),
    queryFn: () =>
      api.get<Paginated<Post>>(`/posts/?repo=${encodeURIComponent(fullName)}`),
    enabled: !!fullName,
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
    mutationFn: (body: string) =>
      api.post<Comment>("/comments/", { post: postId, body }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.comments(postId) });
      qc.invalidateQueries({ queryKey: keys.feed });
    },
  });
}
