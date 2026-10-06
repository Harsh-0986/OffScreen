import type {
  AuthResponse,
  AuthUser,
  ChallengeResponse,
  Discovery,
  DiscoveryResponse,
  Profile,
} from "./types";

/**
 * The API base is public config; the GEMINI_API_KEY never reaches the browser
 * (it lives only in the backend process, SPEC §23).
 */
const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? "http://localhost:8000";

const TOKEN_KEY = "ono.token";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }

  /** 401 means the session is gone and the UI should send the user to sign in. */
  get isUnauthorized() {
    return this.status === 401;
  }
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (typeof window === "undefined") return;
  if (token) window.localStorage.setItem(TOKEN_KEY, token);
  else window.localStorage.removeItem(TOKEN_KEY);
}

type RequestOptions = {
  method?: "GET" | "POST" | "PATCH";
  body?: unknown;
  formData?: FormData;
  /** Set false for the login/signup calls, which run before a token exists. */
  auth?: boolean;
  signal?: AbortSignal;
};

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, formData, auth = true, signal } = options;

  const headers: Record<string, string> = {};
  if (auth) {
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }
  if (body !== undefined) headers["Content-Type"] = "application/json";

  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: formData ?? (body !== undefined ? JSON.stringify(body) : undefined),
    signal,
  });

  if (!response.ok) {
    let detail = `Something went wrong (${response.status}).`;
    try {
      const payload = await response.json();
      if (typeof payload?.detail === "string") detail = payload.detail;
    } catch {
      /* keep the default message; never surface raw HTML */
    }
    throw new ApiError(detail, response.status);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const api = {
  health: () => request<{ status: string }>("/health", { auth: false }),

  // --- auth ---------------------------------------------------------------
  signup: (input: { email: string; password: string; display_name?: string }) =>
    request<AuthResponse>("/api/auth/signup", {
      method: "POST",
      body: input,
      auth: false,
    }),
  login: (input: { email: string; password: string }) =>
    request<AuthResponse>("/api/auth/login", { method: "POST", body: input, auth: false }),
  me: (signal?: AbortSignal) => request<AuthUser>("/api/auth/me", { signal }),

  // --- challenges ---------------------------------------------------------
  today: (signal?: AbortSignal) => request<ChallengeResponse>("/api/challenges/today", { signal }),
  generateChallenge: (forceNew = false, signal?: AbortSignal) =>
    request<ChallengeResponse>("/api/challenges/generate", {
      method: "POST",
      body: { force_new: forceNew },
      signal,
    }),

  // --- discoveries --------------------------------------------------------
  submitDiscovery: (challengeId: string, file: File, signal?: AbortSignal) => {
    const formData = new FormData();
    formData.append("challenge_id", challengeId);
    formData.append("image", file);
    return request<DiscoveryResponse>("/api/discoveries", {
      method: "POST",
      formData,
      signal,
    });
  },
  journal: (signal?: AbortSignal) =>
    request<{ discoveries: Discovery[]; total: number }>("/api/journal", { signal }),
  profile: (signal?: AbortSignal) => request<Profile>("/api/profile", { signal }),
  updateProfile: (display_name: string) =>
    request<Profile>("/api/profile", { method: "PATCH", body: { display_name } }),
};

export { API_BASE };
