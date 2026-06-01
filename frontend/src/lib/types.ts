export interface Author {
  id: number;
  username: string;
  profileimg: string | null;
}

export interface Profile {
  username: string;
  bio: string;
  location: string;
  profileimg: string | null;
  followers_count: number;
  following_count: number;
  posts_count: number;
  is_following: boolean;
  created_at: string;
}

export interface Repo {
  full_name: string;
  name: string;
  owner_login: string;
  owner_avatar_url: string;
  html_url: string;
  description: string;
  homepage: string;
  language: string;
  topics: string[];
  stargazers_count: number;
  forks_count: number;
  open_issues_count: number;
  pushed_at: string | null;
}

export interface Post {
  id: string;
  author: Author;
  caption: string;
  image: string;
  repo: Repo | null;
  created_at: string;
  num_likes: number;
  comments_count: number;
  liked: boolean;
}

export interface Comment {
  id: number;
  post: string;
  parent: number | null;
  author: Author;
  body: string;
  created_at: string;
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface CursorPaginated<T> {
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface TokenPair {
  access: string;
  refresh: string;
}

export interface LiveEvent {
  type: string;
  actor: string;
  title?: string;
  url?: string;
  repo?: string | null;
  post_id?: string | null;
  created_at?: string;
}
