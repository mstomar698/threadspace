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
  Paginated,
  Post,
  Profile,
} from "./types";

export const keys = {
  feed: ["feed"] as const,
  profile: (username: string) => ["profile", username] as const,
  comments: (postId: string) => ["comments", postId] as const,
  search: (q: string) => ["search", q] as const,
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
