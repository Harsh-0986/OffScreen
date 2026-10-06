import type { Metadata } from "next";
import { Fraunces, Inter_Tight } from "next/font/google";

import { AuthProvider } from "@/lib/auth-context";
import "./globals.css";

/** Heavy grotesque for the big statements. */
const display = Inter_Tight({
  variable: "--font-display-face",
  subsets: ["latin"],
  weight: ["600", "700", "800"],
});

/** Quiet serif for reflections and body copy. */
const body = Fraunces({
  variable: "--font-body-face",
  subsets: ["latin"],
  weight: ["300", "400", "500"],
  style: ["normal", "italic"],
});

export const metadata: Metadata = {
  title: "Outside, Not Online",
  description:
    "One photo. One discovery. One reason to go outside. An AI-powered outdoor discovery journal.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${display.variable} ${body.variable} h-full`}>
      <body className="flex min-h-full flex-col bg-paper text-ink">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
