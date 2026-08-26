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
  title: "INFINITUM — La Boîte de la Cour",
  description:
    "1 387 décisions criminelles réelles de la Division d'appel de New York (2015-2023), présentées comme une messagerie : panels, taux de confirmation, signaux statistiques, délibérations multi-agents archivées. Zéro donnée fabriquée.",
  keywords: [
    "judicial analytics", "behavioral matrix", "legal telemetry",
    "NY Appellate Division", "CourtListener", "stylometry", "Monte-Carlo",
    "INFINITUM", "boîte de la cour",
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
