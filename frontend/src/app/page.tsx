import Link from "next/link";

import { SignInOrStart } from "@/components/sign-in-or-start";

export default function Home() {
  return (
    <main className="flex flex-1 flex-col">
      <section className="flex flex-1 flex-col justify-center px-6 py-24 sm:px-10">
        <p className="eyebrow mb-8">An outdoor discovery journal</p>

        <h1 className="font-display text-[clamp(3.5rem,15vw,11rem)] uppercase">
          Outside,
          <br />
          Not Online.
        </h1>

        <div className="mt-12 grid gap-10 sm:grid-cols-2 sm:items-end">
          <p className="max-w-sm text-lg leading-relaxed text-ink-soft">
            One photo. One discovery. One reason to go outside.
          </p>

          <div className="sm:justify-self-end">
            <SignInOrStart />
          </div>
        </div>
      </section>

      <section className="border-t border-line px-6 py-16 sm:px-10">
        <ol className="grid gap-10 sm:grid-cols-3">
          {[
            {
              step: "01",
              title: "Get a challenge",
              body: "One small, specific thing to look for. Five minutes or twenty.",
            },
            {
              step: "02",
              title: "Put the phone down",
              body: "The app has no timer, no feed, and nothing to scroll. Go and look.",
            },
            {
              step: "03",
              title: "Bring back a photo",
              body: "Gemma looks at what you found, tells you what it sees, and scores it.",
            },
          ].map((item) => (
            <li key={item.step}>
              <p className="eyebrow mb-3">{item.step}</p>
              <p className="font-display text-xl tracking-tight">{item.title}</p>
              <p className="mt-2 leading-relaxed text-ink-soft">{item.body}</p>
            </li>
          ))}
        </ol>
      </section>

      <footer className="border-t border-line px-6 py-10 text-sm text-ink-faint sm:px-10">
        <p>
          <span className="font-display tracking-tight">Offscreen</span> — built with
          Gemma and LangGraph.{" "}
          <Link href="/login" className="underline underline-offset-4 hover:text-ink">
            Sign in
          </Link>
        </p>
      </footer>
    </main>
  );
}
