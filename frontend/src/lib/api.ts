import type { TokenPair } from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const API_V1 = `${API_BASE}/api/v1`;

const ACCESS_KEY = "ts_access";
const REFRESH_KEY = "ts_refresh";

/** sessionStorage key for the GitHub sign-in OAuth nonce (login CSRF guard). */
export const GITHUB_NONCE_KEY = "ts_gh_nonce";

export const tokenStore = {
  get access() {
    if (typeof window === "undefined") return null;
    return localStorage.getItem(ACCESS_KEY);
  },
  get refresh() {
    if (typeof window === "undefined") return null;
    return localStorage.getItem(REFRESH_KEY);
  },
  set({ access, refresh }: TokenPair) {
    localStorage.setItem(ACCESS_KEY, access);
    localStorage.setItem(REFRESH_KEY, refresh);
  },
  setAccess(access: string) {
    localStorage.setItem(ACCESS_KEY, access);
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

export class ApiError extends Error {
  status: number;
  data: unknown;
  constructor(status: number, data: unknown) {
    super(`API error ${status}`);
    this.status = status;
    this.data = data;
  }
}

/** Extract a human-friendly message from a DRF error payload. */
export function errorMessage(err: unknown, fallback = "Something went wrong"): string {
  if (err instanceof ApiError && err.data && typeof err.data === "object") {
    const data = err.data as Record<string, unknown>;
    const first = data.detail ?? Object.values(data)[0];
    if (Array.isArray(first)) return String(first[0]);
    if (first) return String(first);
  }
  return err instanceof Error ? err.message : fallback;
}

async function refreshAccessToken(): Promise<string | null> {
  const refresh = tokenStore.refresh;
  if (!refresh) return null;
  const res = await fetch(`${API_V1}/auth/token/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
  });
  if (!res.ok) {
    tokenStore.clear();
    return null;
  }
  const data = (await res.json()) as { access: string };
  tokenStore.setAccess(data.access);
  return data.access;
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  /** When true, sends FormData (for file uploads) instead of JSON. */
  form?: FormData;
  auth?: boolean;
  retry?: boolean;
}

async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, form, auth = true, retry = true } = opts;
  const headers: Record<string, string> = {};
  const url = path.startsWith("http") ? path : `${API_V1}${path}`;

  if (auth && tokenStore.access) {
    headers.Authorization = `Bearer ${tokenStore.access}`;
  }

  let payload: BodyInit | undefined;
  if (form) {
    payload = form;
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  const res = await fetch(url, { method, headers, body: payload });

  if (res.status === 401 && retry && tokenStore.refresh) {
    const newAccess = await refreshAccessToken();
    if (newAccess) {
      return request<T>(path, { ...opts, retry: false });
    }
  }

  if (!res.ok) {
    let data: unknown = null;
    try {
      data = await res.json();
    } catch {
      /* no body */
    }
    throw new ApiError(res.status, data);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  get: <T>(path: string, auth = true) => request<T>(path, { auth }),
  post: <T>(path: string, body?: unknown, auth = true) =>
    request<T>(path, { method: "POST", body, auth }),
  postForm: <T>(path: string, form: FormData) =>
    request<T>(path, { method: "POST", form }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PATCH", body }),
  patchForm: <T>(path: string, form: FormData) =>
    request<T>(path, { method: "PATCH", form }),
  delete: (path: string) => request<void>(path, { method: "DELETE" }),
};
