import type { Metadata } from "next";
import { IBM_Plex_Mono, Newsreader, Public_Sans } from "next/font/google";
import "./globals.css";
import { DealProvider } from "@/lib/deal-context";
import { SourcePanel, SourceProvider } from "@/components/source";
import { Gate } from "@/components/gate";
import { TopBar } from "@/components/top-bar";

const publicSans = Public_Sans({ subsets: ["latin"], variable: "--font-public-sans" });
const newsreader = Newsreader({ subsets: ["latin"], variable: "--font-newsreader" });
const plexMono = IBM_Plex_Mono({ subsets: ["latin"], weight: ["400"], variable: "--font-plex-mono" });

export const metadata: Metadata = {
  title: "Stochastic - reviewer console",
  description: "AI agents work a special-situation deal. A senior human decides.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${publicSans.variable} ${newsreader.variable} ${plexMono.variable}`}>
      <body className="min-h-screen">
        <DealProvider>
          <SourceProvider>
            <TopBar />
            <main><Gate>{children}</Gate></main>
            <SourcePanel />
          </SourceProvider>
        </DealProvider>
      </body>
    </html>
  );
}
