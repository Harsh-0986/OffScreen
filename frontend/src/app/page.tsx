export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 px-6 text-center">
      <h1 className="text-4xl font-semibold tracking-tight sm:text-6xl">
        OUTSIDE,
        <br />
        NOT ONLINE.
      </h1>
      <p className="max-w-md text-neutral-600">
        One photo. One discovery. One reason to go outside.
      </p>
      <a
        href="/today"
        className="rounded-full bg-black px-6 py-3 text-sm font-medium text-white transition hover:bg-neutral-800"
      >
        START EXPLORING
      </a>
    </main>
  );
}
