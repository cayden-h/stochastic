/** What Eric's Electron preload (desktop/preload.js) exposes as window.stochastic. Absent in a browser. */
export interface DesktopBridge {
  isDesktop?: boolean;
  /** Writes the files through the macOS folder dialog. */
  saveFiles?: (files: { url: string; name: string }[]) => Promise<unknown>;
  /** Tells the app the console's first read of the deal is done, so it can show the window and close the splash. */
  appReady?: () => void;
}

declare global {
  interface Window {
    stochastic?: DesktopBridge;
  }
}
