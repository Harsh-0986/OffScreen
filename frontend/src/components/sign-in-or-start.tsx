"use client";

import Link from "next/link";

import { useAuth } from "@/lib/auth-context";

/**
 * The landing page is public so the demo opens on the promise, not a login
 * form. Signed-in visitors go straight to today's challenge.
 */
export function SignInOrStart() {
  const { user, loading } = useAuth();

  if (loading) {
    return <span className="block h-12 w-48 animate-pulse rounded-full bg-line" />;
  }

  if (user) {
    return (
      <Link
        href="/today"
        className="inline-flex h-12 items-center rounded-full bg-ink px-8 text-sm font-semibold tracking-wide text-paper transition hover:bg-ink-soft"
      >
        TODAY&apos;S CHALLENGE
      </Link>
    );
  }

  return (
    <Link
      href="/login"
      className="inline-flex h-12 items-center rounded-full bg-ink px-8 text-sm font-semibold tracking-wide text-paper transition hover:bg-ink-soft"
    >
      START EXPLORING
    </Link>
  );
}
