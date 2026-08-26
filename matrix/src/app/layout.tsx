import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
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

export const metadata: Metadata = {
  title: "Behavioral Matrix — Legally Subjective",
  description:
    "Console d'analyse cognitive judiciaire : 1 387 appels criminels réels (NY Appellate Division, 2015-2023), télémétrie décisionnelle, stylométrie, bootstrap Monte-Carlo et arbitrage multi-agents humain vs IA. Zéro donnée fictive.",
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
    <html lang="fr" suppressHydrationWarning className="dark">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-background text-foreground`}
      >
        {children}
        <Toaster />
      </body>
    </html>
  );
}
