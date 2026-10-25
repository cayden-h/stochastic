// Preload for the console window. It exposes window.stochastic through contextBridge;
// the page gets no Node access (contextIsolation on, nodeIntegration off, sandboxed).

const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("stochastic", {
  isDesktop: true,
  // The console calls this once its first read of the deal has finished, so main can show the window
  // and close the launch splash (design/brand.md).
  appReady: () => ipcRenderer.send("stochastic:app-ready"),
  // A native macOS notification for a question that needs the controller: { title, body }. Clicking it brings the
  // window forward. Fire and forget.
  notify: ({ title, body } = {}) => ipcRenderer.send("stochastic:notify", { title, body }),
  // files: [{ url, name }], url absolute or relative to the API (for example "/deals/d_kequ_nuaire/files/workbook.xlsx").
  // Asks for a folder, downloads each file from the API into it, and shows it in Finder.
  // Resolves to { canceled, folder, files } with the written paths; rejects if any download fails.
  // Electron prefixes errors from the main process with "Error invoking remote method ...: Error:";
  // the console shows the message as it is, so pass on only our own words.
  saveFiles: (files) => ipcRenderer.invoke("stochastic:save-files", files).catch((error) => {
    throw new Error(String(error.message).replace(/^Error invoking remote method '[^']+': (Error: )?/, ""));
  }),
});
