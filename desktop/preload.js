// Preload for the console window. It exposes window.stochastic through contextBridge;
// the page gets no Node access (contextIsolation on, nodeIntegration off, sandboxed).

const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("stochastic", {
  isDesktop: true,
  // files: [{ url, name }], url absolute or relative to the API (for example "/deals/d_kequ_nuaire/files/workbook.xlsx").
  // Asks for a folder, downloads each file from the API into it, and shows it in Finder.
  // Resolves to { canceled, folder, files } with the written paths; rejects if any download fails.
  // Electron prefixes errors from the main process with "Error invoking remote method ...: Error:";
  // the console shows the message as it is, so pass on only our own words.
  saveFiles: (files) => ipcRenderer.invoke("stochastic:save-files", files).catch((error) => {
    throw new Error(String(error.message).replace(/^Error invoking remote method '[^']+': (Error: )?/, ""));
  }),
});
