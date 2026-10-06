"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

type Mode = "signin" | "signup";

export default function LoginPage() {
  // useSearchParams needs a Suspense boundary to stay statically prerenderable.
  return (
    <Suspense fallback={<main className="flex-1" />}>
      <LoginForm />
    </Suspense>
  );
}

function LoginForm() {
  const [mode, setMode] = useState<Mode>("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const { signIn, signUp } = useAuth();
  const router = useRouter();
  const next = useSearchParams().get("next") ?? "/today";

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      if (mode === "signup") {
        await signUp({
          email,
          password,
          display_name: displayName.trim() || undefined,
        });
      } else {
        await signIn({ email, password });
      }
      router.replace(next);
    } catch (caught) {
      setError(
        caught instanceof ApiError ? caught.message : "Could not reach the server. Try again.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center px-6 py-20">
      <Link href="/" className="eyebrow mb-10 hover:!text-ink-soft">
        ← Outside, Not Online
      </Link>

      <h1 className="font-display text-5xl tracking-tight">
        {mode === "signin" ? "Welcome back." : "Start outside."}
      </h1>
      <p className="reflection mt-4 text-lg">
        {mode === "signin"
          ? "Your journal is where you left it."
          : "One account, one journal of things you noticed."}
      </p>

      <form onSubmit={submit} className="mt-12 flex flex-col gap-5">
        {mode === "signup" && (
          <Field
            label="Name"
            value={displayName}
            onChange={setDisplayName}
            placeholder="Optional"
            autoComplete="name"
          />
        )}

        <Field
          label="Email"
          value={email}
          onChange={setEmail}
          type="email"
          required
          autoComplete="email"
        />

        <Field
          label="Password"
          value={password}
          onChange={setPassword}
          type="password"
          required
          minLength={mode === "signup" ? 8 : undefined}
          autoComplete={mode === "signup" ? "new-password" : "current-password"}
        />

        {mode === "signup" && (
          <p className="-mt-2 text-sm text-ink-faint">At least 8 characters.</p>
        )}

        {error && (
          <p role="alert" className="border-l-2 border-clay pl-4 text-sm text-clay">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={busy}
          className="mt-3 inline-flex h-12 items-center justify-center rounded-full bg-ink text-sm font-semibold tracking-wide text-paper transition hover:bg-ink-soft disabled:opacity-50"
        >
          {busy ? "ONE MOMENT" : mode === "signin" ? "SIGN IN" : "CREATE ACCOUNT"}
        </button>
      </form>

      <button
        type="button"
        onClick={() => {
          setMode(mode === "signin" ? "signup" : "signin");
          setError(null);
        }}
        className="mt-8 self-start text-sm text-ink-soft underline underline-offset-4 hover:text-ink"
      >
        {mode === "signin" ? "New here? Create an account" : "Already have an account? Sign in"}
      </button>
    </main>
  );
}

function Field({
  label,
  value,
  onChange,
  type = "text",
  ...rest
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  placeholder?: string;
  required?: boolean;
  minLength?: number;
  autoComplete?: string;
}) {
  return (
    <label className="flex flex-col gap-2">
      <span className="eyebrow">{label}</span>
      <input
        {...rest}
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-12 border-b border-line bg-transparent text-lg outline-none transition focus:border-moss"
      />
    </label>
  );
}
