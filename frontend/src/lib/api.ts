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
 * (it lives only in the backend process).
 *
 * NEXT_PUBLIC_ variables are inlined at build time, so this must be set in
 * frontend/.env.local before `pnpm dev` / `pnpm build`. The root .env is not
 * read by Next.js.
 */
const API_BASE = (
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? "http://localhost:8000"
);

// A production build silently pointing at localhost is a confusing failure to
// debug in a browser, so say so loudly once at startup.
if (process.env.NODE_ENV === "production" && !process.env.NEXT_PUBLIC_API_BASE_URL) {
  console.warn(
    "[offscreen] NEXT_PUBLIC_API_BASE_URL is not set; falling back to localhost:8000. " +
      "Set it in frontend/.env.local and rebuild.",
  );
}

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

/**
 * A request that was cancelled on purpose, e.g. the component unmounted.
 * Callers must ignore these — they are not errors worth showing anyone.
 */
export class RequestAbortedError extends Error {
  constructor() {
    super("Request aborted");
    this.name = "AbortError";
  }
}

export function isAbortError(error: unknown): boolean {
  if (error instanceof RequestAbortedError) return true;
  if (typeof error !== "object" || error === null) return false;
  const name = (error as { name?: unknown }).name;
  return name === "AbortError" || name === "RequestAbortedError";
}

/**
 * Abort a controller for a deliberate cancel.
 *
 * The reason is a real AbortError so that even if it escapes somewhere, it is
 * recognisable and ignorable rather than a bare string that surfaces as an
 * anonymous unhandled rejection.
 */
export function abortOnUnmount(controller: AbortController) {
  controller.abort(new DOMException("Request cancelled", "AbortError"));
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
  /**
   * Collapse concurrent calls into one and reuse a very recent result.
   * The session check runs on mount and again after every navigation, and in
   * dev StrictMode mounts twice, so without this it hammers /api/auth/me.
   */
  dedupe?: boolean;
};

/** How long a deduped GET stays fresh. Short: long enough to stop the bursts. */
const DEDUPE_TTL_MS = 15_000;

type Inflight = { key: string; promise: Promise<unknown> };
let inflight: Inflight | null = null;
const recent = new Map<string, { at: number; value: unknown }>();

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, formData, auth = true, signal, dedupe } = options;

  const headers: Record<string, string> = {};
  let token: string | null = null;
  if (auth) {
    token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }
  if (body !== undefined) headers["Content-Type"] = "application/json";

  // Cached results are keyed by path *and* token so switching accounts, or
  // signing out, can never serve the previous user's session.
  const cacheKey = `${method} ${path} ${token ?? ""}`;
  if (dedupe) {
    const hit = recent.get(cacheKey);
    if (hit && Date.now() - hit.at < DEDUPE_TTL_MS) return hit.value as T;
    if (inflight?.key === cacheKey) return inflight.promise as Promise<T>;
  }

  const run = performRequest<T>(path, { method, body, formData, headers, signal });

  if (dedupe) {
    const tracked = run
      .then((value) => {
        recent.set(cacheKey, { at: Date.now(), value });
        return value;
      })
      .finally(() => {
        if (inflight?.promise === tracked) inflight = null;
      });
    inflight = { key: cacheKey, promise: tracked };
    return tracked;
  }

  return run;
}

async function performRequest<T>(
  path: string,
  options: {
    method: string;
    body?: unknown;
    formData?: FormData;
    headers: Record<string, string>;
    signal?: AbortSignal;
  },
): Promise<T> {
  const { method, body, formData, headers, signal } = options;

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: formData ?? (body !== undefined ? JSON.stringify(body) : undefined),
      signal,
    });
  } catch (cause) {
    throw normaliseFailure(cause, signal);
  }

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

  try {
    return (await response.json()) as T;
  } catch (cause) {
    // Aborting between headers and body rejects here too; the whole body read
    // has to be guarded, not just the fetch call.
    throw normaliseFailure(cause, signal);
  }
}

/**
 * Turn anything thrown during a request into either a typed, ignorable abort or
 * a user-safe API error. Nothing from the network escapes untyped.
 */
function normaliseFailure(cause: unknown, signal?: AbortSignal): Error {
  if (signal?.aborted || isAbortError(cause)) return new RequestAbortedError();
  return new ApiError("Could not reach the server.", 0);
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
  me: (signal?: AbortSignal) => request<AuthUser>("/api/auth/me", { signal, dedupe: true }),

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

/** Drop cached GETs. Called on sign in/out so a new session is never stale. */
export function clearRequestCache() {
  recent.clear();
  inflight = null;
}

export { API_BASE };
