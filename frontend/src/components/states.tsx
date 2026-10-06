/** Calm, non-alarming states (SPEC §38). No spinners screaming for attention. */

export function Thinking({ lines }: { lines: readonly string[] }) {
  return (
    <div className="flex flex-col items-center gap-6 py-24 text-center" role="status">
      <span className="h-8 w-8 animate-spin rounded-full border-2 border-line border-t-moss" />
      {/* The line changes every few seconds so a long wait still feels alive. */}
      <RotatingLine lines={lines} />
      <p className="max-w-xs text-sm text-ink-faint">
        This can take up to half a minute. Close the app if you like — the
        challenge will be waiting.
      </p>
    </div>
  );
}

function RotatingLine({ lines }: { lines: readonly string[] }) {
  return (
    <span className="font-display text-2xl tracking-tight">
      {lines.map((line, index) => (
        <span
          key={line}
          className="animate-[fade_4s_ease-in-out_infinite] first:opacity-100"
          style={{ animationDelay: `${index * 4}s` }}
        >
          {index > 0 ? " " : ""}
          {line}
        </span>
      ))}
    </span>
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
