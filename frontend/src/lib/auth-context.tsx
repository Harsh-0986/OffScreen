"use client";

import { useRouter } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { ApiError, api, setToken } from "@/lib/api";
import type { AuthUser } from "@/lib/types";

type AuthState = {
  user: AuthUser | null;
  /** True until the stored token has been checked, so routes don't bounce. */
  loading: boolean;
  signUp: (input: {
    email: string;
    password: string;
    display_name?: string;
  }) => Promise<void>;
  signIn: (input: { email: string; password: string }) => Promise<void>;
  signOut: () => void;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const controller = new AbortController();

    (async () => {
      try {
        setUser(await api.me(controller.signal));
      } catch (error) {
        // A missing or expired token just means "signed out", not an error to show.
        if (error instanceof ApiError && error.status === 401) setToken(null);
        setUser(null);
      } finally {
        setLoading(false);
      }
    })();

    return () => controller.abort();
  }, []);

  const adopt = useCallback((response: { token: string; user: AuthUser }) => {
    setToken(response.token);
    setUser(response.user);
  }, []);

  const signUp = useCallback<AuthState["signUp"]>(
    async (input) => adopt(await api.signup(input)),
    [adopt],
  );

  const signIn = useCallback<AuthState["signIn"]>(
    async (input) => adopt(await api.login(input)),
    [adopt],
  );

  const signOut = useCallback(() => {
    setToken(null);
    setUser(null);
    router.push("/");
  }, [router]);

  const value = useMemo(
    () => ({ user, loading, signUp, signIn, signOut }),
    [user, loading, signUp, signIn, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside <AuthProvider>");
  return context;
}

/** Send anonymous visitors to sign in, remembering where they were headed. */
export function useRequireAuth(nextPath?: string) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.replace(nextPath ? `/login?next=${encodeURIComponent(nextPath)}` : "/login");
    }
  }, [loading, user, router, nextPath]);

  return { user, loading, ready: !loading && !!user };
}
