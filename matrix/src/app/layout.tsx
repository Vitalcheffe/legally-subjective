import type { Metadata } from "next";
import { Geist, Geist_Mono, Source_Serif_4 } from "next/font/google";
import "./globals.css";
import { Toaster } from "@/components/ui/toaster";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const sourceSerif = Source_Serif_4({
  variable: "--font-source-serif",
  subsets: ["latin"],
  weight: ["400", "600", "700"],
  style: ["normal", "italic"],
});

export const metadata: Metadata = {
  title: "Behavioral Matrix — Legally Subjective",
  description:
    "Plateforme d'analyse décisionnelle judiciaire : 1 387 appels criminels réels (NY Appellate Division, 2015-2023), télémétrie comportementale, stylométrie, inférence bootstrap Monte-Carlo et arbitrage multi-agents humain contre IA. Aucune donnée fictive.",
  keywords: [
    "judicial analytics", "behavioral matrix", "legal telemetry",
    "NY Appellate Division", "CourtListener", "stylometry", "Monte-Carlo",
  ],
  authors: [{ name: "VitalCheffe" }],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="fr" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} ${sourceSerif.variable} antialiased bg-background text-foreground`}
      >
        {children}
        <Toaster />
      </body>
    </html>
  );
}
