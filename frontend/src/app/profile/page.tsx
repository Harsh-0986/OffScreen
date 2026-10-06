"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Nav } from "@/components/nav";
import { ErrorState } from "@/components/states";
import { ApiError, api } from "@/lib/api";
import { useAuth, useRequireAuth } from "@/lib/auth-context";
import type { Profile } from "@/lib/types";

export default function ProfilePage() {
  const { ready } = useRequireAuth("/profile");
  const { user, signOut } = useAuth();

  const [profile, setProfile] = useState<Profile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!ready) return;
    const controller = new AbortController();

    api
      .profile(controller.signal)
      .then((loaded) => {
        setProfile(loaded);
        setName(loaded.display_name);
      })
      .catch((caught) => {
        if (controller.signal.aborted) return;
        setError(caught instanceof ApiError ? caught.message : "Could not load your profile.");
      });

    return () => controller.abort();
  }, [ready]);

  async function saveName(event: React.FormEvent) {
    event.preventDefault();
    setSaving(true);
    setSaved(false);
    try {
      const updated = await api.updateProfile(name.trim());
      setProfile(updated);
      setSaved(true);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not save your name.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <Nav active="profile" />
      <main className="mx-auto w-full max-w-2xl flex-1 px-6 py-16">
        <p className="eyebrow">{user?.email}</p>
        <h1 className="font-display mt-4 text-[clamp(2.5rem,8vw,4.5rem)] tracking-tight">
          {profile?.display_name ?? "You"}
        </h1>

        {error && <ErrorState message={error} />}

        {profile && (
          <>
            <dl className="mt-14 grid grid-cols-2 gap-x-8 gap-y-10 sm:grid-cols-4">
              <Stat label="Discoveries" value={profile.discoveries_count} />
              <Stat label="Points" value={profile.total_points} />
              <Stat label="Streak" value={profile.current_streak} />
              <Stat label="Minutes out" value={profile.outdoor_minutes_estimate} />
            </dl>

            <section className="mt-16 border-t border-line pt-10">
              <h2 className="eyebrow">What you notice</h2>
              {Object.keys(profile.favorite_categories).length === 0 ? (
                <p className="reflection mt-4 text-lg">
                  Complete a discovery and this fills in.
                </p>
              ) : (
                <ul className="mt-6 space-y-3">
                  {Object.entries(profile.favorite_categories)
                    .sort(([, a], [, b]) => b - a)
                    .map(([category, weight]) => (
                      <li key={category} className="flex items-center gap-4">
                        <span className="w-28 shrink-0 capitalize">{category}</span>
                        <span className="h-2 bg-moss/70" style={{ width: `${weight * 24}px` }} />
                        <span className="text-sm tabular-nums text-ink-faint">
                          {weight.toFixed(0)}
                        </span>
                      </li>
                    ))}
                </ul>
              )}
            </section>

            <section className="mt-16 border-t border-line pt-10">
              <h2 className="eyebrow">Your name</h2>
              <form onSubmit={saveName} className="mt-6 flex flex-wrap items-end gap-4">
                <input
                  value={name}
                  onChange={(event) => {
                    setName(event.target.value);
                    setSaved(false);
                  }}
                  maxLength={80}
                  aria-label="Display name"
                  className="h-12 min-w-0 flex-1 border-b border-line bg-transparent text-lg outline-none transition focus:border-moss"
                />
                <button
                  type="submit"
                  disabled={saving || !name.trim()}
                  className="h-12 rounded-full border border-ink px-6 text-sm font-semibold tracking-wide transition hover:bg-ink hover:text-paper disabled:opacity-40"
                >
                  {saving ? "SAVING" : "SAVE"}
                </button>
              </form>
              {saved && <p className="mt-3 text-sm text-moss">Saved.</p>}
            </section>
          </>
        )}

        <div className="mt-16 flex flex-wrap gap-6 border-t border-line pt-10 text-sm text-ink-faint">
          <Link href="/today" className="underline underline-offset-4 hover:text-ink">
            Today&apos;s challenge
          </Link>
          <Link href="/journal" className="underline underline-offset-4 hover:text-ink">
            Journal
          </Link>
          <button type="button" onClick={signOut} className="underline underline-offset-4 hover:text-ink">
            Sign out
          </button>
        </div>
      </main>
    </>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <dt className="eyebrow">{label}</dt>
      <dd className="font-display mt-1 text-4xl tabular-nums tracking-tight">{value}</dd>
    </div>
  );
}
