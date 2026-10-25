// Renders assets/icon.svg to assets/icon.png (1024 by 1024, transparent corners) with Electron's own Chromium,
// then builds assets/icon.icns with macOS sips and iconutil. Run with `npm run icon` in desktop/.
// The SVG is the source; commit all three files after a change (docs/design/brand.md).

const { app, BrowserWindow } = require("electron");
const { execFileSync } = require("node:child_process");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const ASSETS = path.join(__dirname, "..", "assets");
const SIZE = 1024;

app.dock?.hide();
app.disableHardwareAcceleration();

app.whenReady().then(async () => {
  const svg = fs.readFileSync(path.join(ASSETS, "icon.svg"), "utf8");
  const html = `<!doctype html><html><head><style>html,body{margin:0;background:transparent}svg{display:block;width:${SIZE}px;height:${SIZE}px}</style></head><body>${svg}</body></html>`;
  const win = new BrowserWindow({
    width: SIZE, height: SIZE, show: false, transparent: true, frame: false, backgroundColor: "#00000000",
    webPreferences: { offscreen: true, javascript: false },
  });
  win.webContents.setFrameRate(1);
  await win.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(html)}`);
  await new Promise((resolve) => setTimeout(resolve, 300));
  const image = (await win.webContents.capturePage()).resize({ width: SIZE, height: SIZE, quality: "best" });
  const png = path.join(ASSETS, "icon.png");
  fs.writeFileSync(png, image.toPNG());

  const set = fs.mkdtempSync(path.join(os.tmpdir(), "stochastic-icon-")) + "/icon.iconset";
  fs.mkdirSync(set);
  for (const size of [16, 32, 128, 256, 512]) {
    execFileSync("sips", ["-z", String(size), String(size), png, "--out", path.join(set, `icon_${size}x${size}.png`)], { stdio: "ignore" });
    execFileSync("sips", ["-z", String(size * 2), String(size * 2), png, "--out", path.join(set, `icon_${size}x${size}@2x.png`)], { stdio: "ignore" });
  }
  execFileSync("iconutil", ["-c", "icns", set, "-o", path.join(ASSETS, "icon.icns")]);
  console.log(`wrote ${png} and ${path.join(ASSETS, "icon.icns")}`);
  app.quit();
}).catch((error) => { console.error(error); app.exit(1); });
