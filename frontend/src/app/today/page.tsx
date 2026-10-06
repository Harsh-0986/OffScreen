"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Nav } from "@/components/nav";
import { ErrorState, Thinking } from "@/components/states";
import { ApiError, abortOnUnmount, api, isAbortError } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth-context";
import { THINKING_LINES, type Challenge } from "@/lib/types";

/** Where the user goes after pressing START: mission mode. */
export default function TodayPage() {
  const { ready } = useRequireAuth("/today");
  const router = useRouter();

  const [challenge, setChallenge] = useState<Challenge | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Starts false and is only set by the request, so no state is written on mount.
  const [loaded, setLoaded] = useState(false);
  const loading = !loaded && !error;

  useEffect(() => {
    if (!ready) return;

    const controller = new AbortController();

    api
      .today(controller.signal)
      .then((response) => {
        setChallenge(response.challenge);
        setNote(response.personalization_note);
      })
      .catch((caught) => {
        if (isAbortError(caught) || controller.signal.aborted) return;
        setError(caught instanceof ApiError ? caught.message : "Could not load today's challenge.");
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoaded(true);
      });

    return () => abortOnUnmount(controller);
  }, [ready]);

  // Keep tomorrow's challenge warm so the morning wait is short.
  usePrefetchTomorrow(ready, challenge?.id);

  if (!ready) return <main className="flex-1" />;

  return (
    <>
      <Nav active="today" />
      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col justify-center px-6 py-20">
        {loading && <Thinking lines={THINKING_LINES} title="Generating today's discovery" />}

        {error && !loading && (
          <ErrorState message={error} onRetry={() => window.location.reload()} />
        )}

        {challenge && !loading && (
          <>
            <p className="eyebrow">Today&apos;s discovery</p>

            <h1 className="font-display mt-8 text-[clamp(2.75rem,9vw,6rem)] tracking-tight">
              {challenge.title}
            </h1>

            <p className="mt-8 text-2xl leading-snug">{challenge.prompt}</p>

            <dl className="mt-10 flex flex-wrap gap-x-10 gap-y-4">
              <Detail label="About" value={`~${challenge.estimated_minutes} min`} />
              <Detail label="Difficulty" value={`${challenge.difficulty} / 4`} />
              <Detail label="Looking for" value={challenge.category} />
            </dl>

            <div className="mt-14 flex flex-col gap-6">
              <button
                type="button"
                onClick={() =>
                  router.push(`/mission?challenge_id=${encodeURIComponent(challenge.id)}`)
                }
                className="inline-flex h-14 w-full max-w-xs items-center justify-center rounded-full bg-ink text-sm font-semibold tracking-[0.15em] text-paper transition hover:bg-ink-soft"
              >
                START ADVENTURE
              </button>

              {note && <p className="reflection max-w-md text-base">{note}</p>}
            </div>
          </>
        )}
      </main>
    </>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="eyebrow">{label}</dt>
      <dd className="mt-1 capitalize">{value}</dd>
    </div>
  );
}

/**
 * Ask the backend to generate tomorrow's challenge while the user is idle here.
 * Failures are silent: it is a bonus, not something the user asked for.
 */
function usePrefetchTomorrow(ready: boolean, currentId: string | undefined) {
  useEffect(() => {
    if (!ready || !currentId) return;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      api.generateChallenge(true, controller.signal).catch(() => {});
    }, 4000);
    return () => {
      clearTimeout(timer);
      abortOnUnmount(controller);
    };
  }, [ready, currentId]);
}
