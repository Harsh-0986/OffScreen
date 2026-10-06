"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useRef, useState } from "react";

import { ErrorState } from "@/components/states";
import { api } from "@/lib/api";

const MAX_BYTES = 10 * 1024 * 1024;

export default function SubmitPage() {
  return (
    <Suspense fallback={<main className="flex-1" />}>
      <Submit />
    </Suspense>
  );
}

function Submit() {
  const router = useRouter();
  const challengeId = useSearchParams().get("challenge_id");
  const cameraInput = useRef<HTMLInputElement>(null);

  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function choose(selected: File | undefined) {
    setError(null);
    if (!selected) return;

    if (!selected.type.startsWith("image/")) {
      setError("That file isn't a photo. Try a JPEG, PNG, or WebP.");
      return;
    }
    if (selected.size > MAX_BYTES) {
      setError("That photo is too large. Keep it under 10 MB.");
      return;
    }

    setFile(selected);
    setPreview((old) => {
      if (old) URL.revokeObjectURL(old);
      return URL.createObjectURL(selected);
    });
  }

  async function submit() {
    if (!file || !challengeId) return;
    setBusy(true);
    setError(null);

    try {
      const response = await api.submitDiscovery(challengeId, file);
      sessionStorage.setItem("ono:last-discovery", JSON.stringify(response.discovery));
      router.push("/result");
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Could not submit that photo. Try again.",
      );
      setBusy(false);
    }
  }

  if (!challengeId) {
    return (
      <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col justify-center px-6 py-20">
        <ErrorState message="We lost track of which challenge this was. Start again from today." />
      </main>
    );
  }

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col justify-center px-6 py-20">
      <p className="eyebrow">One photograph</p>

      <h1 className="font-display mt-6 text-[clamp(2.5rem,8vw,4.5rem)] tracking-tight">
        What did you find?
      </h1>

      {preview ? (
        <figure className="photo-frame mt-12">
          {/* Blob URL of a local file; next/image cannot optimize it. */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={preview}
            alt="Your photograph, ready to submit"
            className="aspect-square w-full object-cover"
          />
        </figure>
      ) : (
        <div className="mt-12 flex flex-col gap-4 sm:flex-row">
          <input
            ref={cameraInput}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            capture="environment"
            className="sr-only"
            onChange={(event) => choose(event.target.files?.[0])}
          />
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            className="sr-only"
            id="library-upload"
            onChange={(event) => choose(event.target.files?.[0])}
          />

          <label
            htmlFor="library-upload"
            className="inline-flex h-14 flex-1 cursor-pointer items-center justify-center rounded-full border border-ink text-sm font-semibold tracking-[0.15em] transition hover:bg-ink hover:text-paper"
          >
            UPLOAD PHOTO
          </label>
          <button
            type="button"
            onClick={() => cameraInput.current?.click()}
            className="inline-flex h-14 flex-1 items-center justify-center rounded-full bg-ink text-sm font-semibold tracking-[0.15em] text-paper transition hover:bg-ink-soft"
          >
            TAKE PHOTO
          </button>
        </div>
      )}

      {error && (
        <p role="alert" className="mt-6 border-l-2 border-clay pl-4 text-sm text-clay">
          {error}
        </p>
      )}

      <div className="mt-10">
        <button
          type="button"
          onClick={submit}
          disabled={!file || busy}
          className="inline-flex h-14 w-full items-center justify-center rounded-full bg-moss text-sm font-semibold tracking-[0.15em] text-paper transition hover:bg-moss/90 disabled:opacity-40"
        >
          {busy ? "Gemma is looking..." : "SUBMIT DISCOVERY"}
        </button>
        <p className="reflection mt-4 text-center text-sm">
          {busy ? "Looking closely. This takes up to fifteen seconds." : " "}
        </p>
      </div>
    </main>
  );
}
