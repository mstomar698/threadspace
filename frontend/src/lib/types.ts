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
  github_login: string | null;
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

/** Slim repo shape returned by the composer autofill endpoint. */
export interface RepoSuggestion {
  full_name: string;
  name: string;
  owner_login: string;
  description: string;
  language: string;
  stargazers_count: number;
}

export interface Post {
  id: string;
  author: Author;
  caption: string;
  image: string | null;
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
  replies_count: number;
  created_at: string;
}

export interface ChatMessage {
  id: number;
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

export interface GitHubAccount {
  login: string;
  avatar_url: string;
  scopes: string;
  connected_at: string;
}

export interface GitHubAccountStatus extends Partial<GitHubAccount> {
  connected: boolean;
}

export interface GithubLoginResult {
  access: string;
  refresh: string;
  username: string;
  created: boolean;
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
