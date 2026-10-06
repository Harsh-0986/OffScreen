"use client";

import Link from "next/link";
import { useCallback, useEffect, useState, useSyncExternalStore } from "react";

import { Nav } from "@/components/nav";
import { EmptyState } from "@/components/states";
import { imageSrc } from "@/lib/image";
import type { Discovery } from "@/lib/types";

const LAST_KEY = "ono:last-discovery";

/**
 * The result is handed over in sessionStorage by /submit. Reading it as an
 * external store keeps hydration correct and avoids setting state in an effect.
 *
 * `getSnapshot` must return a stable reference or React re-renders forever, so
 * the parse is cached and only redone when the stored string changes.
 */
function useLastDiscovery(): Discovery | null {
  // sessionStorage changes are not observable, so this never fires.
  const subscribe = useCallback(() => () => {}, []);
  const getSnapshot = useCallback((): Discovery | null => {
    const raw = window.sessionStorage.getItem(LAST_KEY);
    if (!raw) return null;
    if (raw === cache.raw) return cache.value;
    try {
      cache = { raw, value: JSON.parse(raw) as Discovery };
    } catch {
      cache = { raw, value: null };
    }
    return cache.value;
  }, []);
  // The server has no session, so it always renders the empty state first.
  const getServerSnapshot = useCallback(() => null, []);

  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}

let cache: { raw: string | null; value: Discovery | null } = { raw: null, value: null };

export default function ResultPage() {
  const discovery = useLastDiscovery();

  if (!discovery) {
    return (
      <>
        <Nav />
        <main className="mx-auto w-full max-w-3xl flex-1 px-6 py-20">
          <EmptyState
            title="No discovery yet."
            body="Go outside and find something. Come back with a photograph."
            action={
              <Link
                href="/today"
                className="inline-flex h-12 items-center rounded-full bg-ink px-8 text-sm font-semibold tracking-wide text-paper"
              >
                TODAY&apos;S CHALLENGE
              </Link>
            }
          />
        </main>
      </>
    );
  }

  return (
    <>
      <Nav />
      <main className="mx-auto w-full max-w-3xl flex-1 px-6 py-16">
        <p className="eyebrow">{discovery.completed ? "Discovery found" : "Not this time"}</p>

        <h1 className="font-display mt-6 text-[clamp(2.5rem,8vw,5rem)] tracking-tight">
          {discovery.title}
        </h1>

        <figure className="photo-frame mt-12">
          {/* Served by the backend from /uploads. */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={imageSrc(discovery.image_url)}
            alt={discovery.visual_description || discovery.title}
            className="aspect-square w-full object-cover"
          />
        </figure>

        <div className="mt-14 grid gap-10 sm:grid-cols-[auto_1fr] sm:gap-16">
          <ScoreReveal score={discovery.score} />

          <div className="flex flex-col gap-6">
            <p className="text-xl leading-relaxed">{discovery.feedback}</p>

            {discovery.description && (
              <p className="reflection text-lg">{discovery.description}</p>
            )}

            {discovery.interesting_detail && (
              <p className="border-l-2 border-moss pl-5 text-base text-ink-soft">
                {discovery.interesting_detail}
              </p>
            )}

            {discovery.visual_description && (
              <p className="text-base text-ink-faint">
                <span className="eyebrow mr-2">What Gemma saw</span>
                {discovery.visual_description}
              </p>
            )}

            <p className="eyebrow">
              +{discovery.points_awarded} discovery points
              {discovery.confidence > 0 && ` · ${Math.round(discovery.confidence * 100)}% confident`}
            </p>
          </div>
        </div>

        <div className="mt-16 flex flex-wrap gap-4 border-t border-line pt-10">
          <Link
            href="/journal"
            className="inline-flex h-12 items-center rounded-full bg-ink px-8 text-sm font-semibold tracking-wide text-paper transition hover:bg-ink-soft"
          >
            VIEW JOURNAL
          </Link>
          <Link
            href="/today"
            className="inline-flex h-12 items-center rounded-full border border-ink px-8 text-sm font-semibold tracking-wide transition hover:bg-ink hover:text-paper"
          >
            DONE FOR TODAY
          </Link>
        </div>
      </main>
    </>
  );
}

/** Counts up to the score once, quickly (SPEC §36). */
function ScoreReveal({ score }: { score: number }) {
  const [shown, setShown] = useState(0);

  useEffect(() => {
    if (score <= 0) return; // nothing to count up to
    const duration = 700;
    const start = performance.now();
    let frame = 0;

    const tick = (now: number) => {
      const progress = Math.min(1, (now - start) / duration);
      setShown(Math.round(score * (1 - (1 - progress) ** 3)));
      if (progress < 1) frame = requestAnimationFrame(tick);
    };

    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [score]);

  return (
    <div>
      <p className="eyebrow">Score</p>
      <p className="font-display mt-2 text-[clamp(4rem,14vw,7rem)] tabular-nums leading-none text-moss">
        {shown}
        <span className="text-ink-faint">/10</span>
      </p>
    </div>
  );
}
