import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Legally Subjective — Subjectivity, measured.",
  description:
    "An open, zero-budget experiment measuring the ceiling of Supreme Court vote predictability with public data. 569 argued cases, 1,778 opinions, one sealed test.",
  other: {
    referrer: "no-referrer",
  },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
