"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

/**
 * Mission mode: the whole point is that this screen has nothing to do
 * (SPEC §5). One message, one button, then get out of the app.
 */
export default function MissionPage() {
  return (
    <Suspense fallback={<main className="flex-1" />}>
      <Mission />
    </Suspense>
  );
}

function Mission() {
  const router = useRouter();
  const challengeId = useSearchParams().get("challenge_id");
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => setSeconds((value) => value + 1), 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <main className="flex flex-1 flex-col items-center justify-center px-6 py-24 text-center">
      <p className="eyebrow">Mission started</p>

      <h1 className="font-display mt-10 max-w-3xl text-[clamp(2.5rem,8vw,5.5rem)] tracking-tight">
        Close this app.
        <br />
        Go outside.
      </h1>

      <p className="reflection mt-10 max-w-md text-xl">
        Your mission has started. Find the thing. Photograph it. Come back when
        you have.
      </p>

      <p className="eyebrow mt-12 tabular-nums">
        {String(Math.floor(seconds / 60)).padStart(2, "0")}:
        {String(seconds % 60).padStart(2, "0")} outside
      </p>

      <button
        type="button"
        disabled={!challengeId}
        onClick={() =>
          challengeId && router.push(`/submit?challenge_id=${encodeURIComponent(challengeId)}`)
        }
        className="mt-14 inline-flex h-14 items-center justify-center rounded-full border border-ink px-10 text-sm font-semibold tracking-[0.15em] transition hover:bg-ink hover:text-paper disabled:opacity-40"
      >
        I&apos;M BACK
      </button>
    </main>
  );
}
