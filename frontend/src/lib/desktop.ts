/** What desktop/main.js answers for saveFiles: the folder and the written paths, or canceled with nothing written. */
export interface SaveFilesResult { canceled: boolean; folder: string | null; files: string[] }

/** What Eric's Electron preload (desktop/preload.js) exposes as window.stochastic. Absent in a browser. */
export interface DesktopBridge {
  isDesktop?: boolean;
  /** Writes the files through the macOS folder dialog. `canceled` when the controller closed the dialog. */
  saveFiles?: (files: { url: string; name: string }[]) => Promise<SaveFilesResult>;
  /** Tells the app the console's first read of the deal is done, so it can show the window and close the splash. */
  appReady?: () => void;
}

declare global {
  interface Window {
    stochastic?: DesktopBridge;
  }
}
