import type { Metadata } from "next";
import { Newsreader, Inter, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";
import { Toaster } from "@/components/ui/toaster";

const newsreader = Newsreader({
  variable: "--font-newsreader",
  subsets: ["latin"],
  style: ["normal", "italic"],
  weight: ["400", "500", "600"],
});

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

const plexMono = IBM_Plex_Mono({
  variable: "--font-plex-mono",
  subsets: ["latin"],
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: "Legally Subjective — Subjectivity, measured.",
  description:
    "The open standard for the measured identity of legal actors. Would you still be free tonight if your judge had been one door down? Not a prediction. A record.",
  keywords: [
    "legal analytics",
    "judicial analytics",
    "subjectivity fingerprint",
    "judges",
    "open standard",
    "LS-1.0",
  ],
  authors: [{ name: "Legally Subjective" }],
  openGraph: {
    title: "Legally Subjective — Subjectivity, measured.",
    description:
      "Would you still be free tonight if your judge had been one door down? Not a prediction. A record.",
    siteName: "Legally Subjective",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Legally Subjective — Subjectivity, measured.",
    description:
      "Would you still be free tonight if your judge had been one door down? Not a prediction. A record.",
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
        className={`${newsreader.variable} ${inter.variable} ${plexMono.variable} antialiased bg-background text-foreground`}
      >
        {children}
        <Toaster />
      </body>
    </html>
  );
}
