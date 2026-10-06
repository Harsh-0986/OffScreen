"use client";

import { useEffect, useState } from "react";

/**
 * Waiting states (SPEC §38).
 *
 * Gemma takes up to ~35s on a free tier, which is long enough that a spinner
 * reads as "broken". So: one line at a time, a slow progress rule that never
 * pretends to know the end, and honest copy about how long it can take.
 */
export function Thinking({
  lines,
  title = "Finding something interesting",
  hint = "Gemma writes a new challenge from scratch each time. This usually takes under a minute — you can close the app and come back.",
}: {
  lines: readonly string[];
  title?: string;
  hint?: string;
}) {
  const [index, setIndex] = useState(0);
  const [seconds, setSeconds] = useState(0);

  // One line at a time, advancing slowly.
  useEffect(() => {
    const timer = setInterval(() => {
      setIndex((current) => (current + 1) % lines.length);
    }, 4000);
    return () => clearInterval(timer);
  }, [lines.length]);

  useEffect(() => {
    const timer = setInterval(() => setSeconds((value) => value + 1), 1000);
    return () => clearInterval(timer);
  }, []);

  // Fills over ~45s then stops. It is deliberately not a true progress bar:
  // pretending to know when the model will finish is worse than not showing one.
  const progress = Math.min(0.92, seconds / 45);

  return (
    <div className="flex flex-col items-center py-24 text-center" role="status" aria-live="polite">
      <p className="eyebrow">{title}</p>

      <p className="font-display mt-8 h-20 text-[clamp(1.75rem,5vw,3rem)] tracking-tight">
        <span key={index} className="animate-[rise_500ms_ease-out_both]">
          {lines[index]}
        </span>
      </p>

      <div className="mt-4 h-px w-56 overflow-hidden bg-line" aria-hidden="true">
        <div
          className="h-full bg-moss transition-[width] duration-1000 ease-linear"
          style={{ width: `${progress * 100}%` }}
        />
      </div>

      <p className="eyebrow mt-4 tabular-nums">
        {String(Math.floor(seconds / 60)).padStart(2, "0")}:
        {String(seconds % 60).padStart(2, "0")}
      </p>

      <p className="reflection mt-10 max-w-sm text-base">{hint}</p>
    </div>
  );
}

export function EmptyState({
  title,
  body,
  action,
}: {
  title: string;
  body: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-start gap-4 border-t border-line py-20">
      <p className="font-display text-3xl tracking-tight">{title}</p>
      <p className="max-w-md leading-relaxed text-ink-soft">{body}</p>
      {action}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="border border-clay/30 bg-clay-soft px-6 py-5" role="alert">
      <p className="font-display text-lg tracking-tight">The AI couldn&apos;t judge this one.</p>
      <p className="mt-2 leading-relaxed text-ink-soft">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-4 text-sm font-semibold tracking-wide text-clay underline underline-offset-4"
        >
          TRY AGAIN
        </button>
      )}
    </div>
  );
}
