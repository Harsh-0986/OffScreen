"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Nav } from "@/components/nav";
import { EmptyState, ErrorState, Thinking } from "@/components/states";
import { API_BASE, ApiError, abortOnUnmount, api, isAbortError } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth-context";
import { THINKING_LINES, type Discovery } from "@/lib/types";

export default function JournalPage() {
  const { ready } = useRequireAuth("/journal");

  const [discoveries, setDiscoveries] = useState<Discovery[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!ready) return;
    const controller = new AbortController();

    api
      .journal(controller.signal)
      .then((response) => setDiscoveries(response.discoveries))
      .catch((caught) => {
        if (isAbortError(caught) || controller.signal.aborted) return;
        setError(caught instanceof ApiError ? caught.message : "Could not load your journal.");
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => abortOnUnmount(controller);
  }, [ready]);

  return (
    <>
      <Nav active="journal" />
      <main className="mx-auto w-full max-w-5xl flex-1 px-6 py-16">
        <p className="eyebrow">Your week outside</p>

        {loading && <Thinking lines={THINKING_LINES} title="Opening your journal" />}

        {error && !loading && <ErrorState message={error} />}

        {!loading && !error && discoveries.length === 0 && (
          <EmptyState
            title="No discoveries yet."
            body="Go outside and find something. Your journal fills up as you do."
            action={
              <Link
                href="/today"
                className="inline-flex h-12 items-center rounded-full bg-ink px-8 text-sm font-semibold tracking-wide text-paper"
              >
                GET A CHALLENGE
              </Link>
            }
          />
        )}

        {discoveries.length > 0 && (
          <ul className="mt-12 grid gap-x-8 gap-y-14 sm:grid-cols-2 lg:grid-cols-3">
            {discoveries.map((discovery, index) => (
              <JournalEntry key={discovery.id} discovery={discovery} index={index} />
            ))}
          </ul>
        )}
      </main>
    </>
  );
}

function JournalEntry({ discovery, index }: { discovery: Discovery; index: number }) {
  return (
    <li
      className="animate-[fade_400ms_ease-out_both]"
      style={{ animationDelay: `${Math.min(index, 8) * 45}ms` }}
    >
      <figure className="photo-frame">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={`${API_BASE}${discovery.image_url}`}
          alt={discovery.visual_description || discovery.title}
          loading="lazy"
          className="aspect-square w-full object-cover"
        />
      </figure>

      <div className="mt-4 flex items-baseline justify-between gap-4">
        <h2 className="font-display text-lg tracking-tight">{discovery.title}</h2>
        <span
          className={
            discovery.completed
              ? "text-sm font-semibold tabular-nums text-moss"
              : "text-sm font-semibold tabular-nums text-ink-faint"
          }
        >
          {discovery.score}/10
        </span>
      </div>

      <p className="mt-1 text-sm text-ink-faint">
        {new Date(discovery.created_at).toLocaleDateString(undefined, {
          month: "short",
          day: "numeric",
        })}
        {!discovery.completed && " · not this time"}
      </p>

      {discovery.feedback && (
        <p className="mt-3 text-sm leading-relaxed text-ink-soft">{discovery.feedback}</p>
      )}
    </li>
  );
}
