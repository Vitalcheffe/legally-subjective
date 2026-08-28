import type { Metadata } from "next";
import { Space_Grotesk, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";
import { Toaster } from "@/components/ui/toaster";

/* UI-1.0 EXHIBIT — Grotesk speaks, Mono measures. Two fonts. No serif. */
const grotesk = Space_Grotesk({
  variable: "--font-grotesk",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const plexMono = IBM_Plex_Mono({
  variable: "--font-plex-mono",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

export const metadata: Metadata = {
  title: "You don't pick your judge. · Legally Subjective",
  description:
    "LS-1.0: the open standard that measures the subjectivity of the bench from filed records. Would you still be free tonight — if your judge had been one door down? Not a prediction. A record.",
  keywords: [
    "legal analytics",
    "judicial analytics",
    "subjectivity fingerprint",
    "judges",
    "open standard",
    "LS-1.0",
    "one door down",
  ],
  authors: [{ name: "Legally Subjective" }],
  openGraph: {
    title: "You don't pick your judge. · Legally Subjective",
    description:
      "Would you still be free tonight — if your judge had been one door down? Not a prediction. A record.",
    siteName: "Legally Subjective",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "You don't pick your judge. · Legally Subjective",
    description:
      "Would you still be free tonight — if your judge had been one door down? Not a prediction. A record.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${grotesk.variable} ${plexMono.variable} antialiased bg-background text-foreground`}
      >
        {children}
        <Toaster />
      </body>
    </html>
  );
}
