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
  title: "Offscreen",
  description:
    "A photo walk, one challenge at a time. Offscreen gives you one small outdoor challenge a day — go find it, photograph it, and let Gemma judge what you brought back.",
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
