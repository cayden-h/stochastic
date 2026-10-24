import type { Metadata } from "next";
import { DM_Sans, IBM_Plex_Mono, Instrument_Serif, Public_Sans } from "next/font/google";
import "./globals.css";
import { DealProvider } from "@/lib/deal-context";
import { EditProvider } from "@/lib/edit-context";
import { Companion } from "@/components/companion";
import { SourcePanel, SourceProvider } from "@/components/source";
import { Shell } from "@/components/shell";

// The v3 type: DM Sans for the UI (optical size fixed at 14, as in the frames), Instrument Serif for page titles,
// IBM Plex Mono for ids and counts, Public Sans for button labels.
const dmSans = DM_Sans({ subsets: ["latin"], axes: ["opsz"], variable: "--font-dm-sans" });
const instrumentSerif = Instrument_Serif({ subsets: ["latin"], weight: "400", variable: "--font-instrument-serif" });
const plexMono = IBM_Plex_Mono({ subsets: ["latin"], weight: ["400"], variable: "--font-plex-mono" });
const publicSans = Public_Sans({ subsets: ["latin"], weight: ["600"], variable: "--font-public-sans" });

export const metadata: Metadata = {
  title: "Stochastic - controller console",
  description: "Merge an add-on company into the platform, flag the lines a human must decide, and test the lender limit.",
};

// In the Electron window (titleBarStyle hiddenInset) the sidebar leaves room for the traffic lights. Set before paint.
const ELECTRON = `if (/Electron\\//.test(navigator.userAgent)) document.documentElement.dataset.electron = "";`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${dmSans.variable} ${instrumentSerif.variable} ${plexMono.variable} ${publicSans.variable}`}
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: ELECTRON }} />
      </head>
      <body>
        <DealProvider>
          <EditProvider>
            <SourceProvider>
              <Shell>{children}</Shell>
              <SourcePanel />
            </SourceProvider>
            <Companion />
          </EditProvider>
        </DealProvider>
      </body>
    </html>
  );
}
