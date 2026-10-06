import Link from "next/link";

/**
 * Minimal app chrome (SPEC §21): four destinations, no badges, no counters
 * pulling you back in.
 */
export function Nav({ active }: { active?: "today" | "journal" | "profile" }) {
  const items = [
    { key: "today", href: "/today", label: "Today" },
    { key: "journal", href: "/journal", label: "Journal" },
    { key: "profile", href: "/profile", label: "You" },
  ] as const;

  return (
    <nav className="flex items-center justify-between border-b border-line px-6 sm:px-10">
      <Link href="/" className="font-display text-sm uppercase tracking-tight">
        Offscreen
      </Link>

      <ul className="flex items-center gap-6 sm:gap-9">
        {items.map((item) => (
          <li key={item.key}>
            <Link
              href={item.href}
              aria-current={active === item.key ? "page" : undefined}
              className={
                active === item.key
                  ? "eyebrow !text-ink"
                  : "eyebrow transition hover:!text-ink-soft"
              }
            >
              {item.label}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
