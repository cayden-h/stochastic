// The Agent House (frame V3-6) during a paced run: the WebGL canvas draws a real picture (not blank), the agents'
// states follow the run, notes fly between rooms, and the page asks nothing of any host but localhost.
import { inflateSync } from "node:zlib";
import { expect, open, test } from "./support/fixtures";
import { begin, nav } from "./support/flows";

/** Decodes an 8-bit RGB or RGBA PNG (what Chromium's screenshots are) into its pixels. */
function pixels(png: Buffer): { width: number; height: number; rgba: (x: number, y: number) => number[] } {
  let pos = 8, width = 0, height = 0, type = 0;
  const idat: Buffer[] = [];
  while (pos < png.length) {
    const len = png.readUInt32BE(pos), kind = png.toString("ascii", pos + 4, pos + 8), data = png.subarray(pos + 8, pos + 8 + len);
    if (kind === "IHDR") { width = data.readUInt32BE(0); height = data.readUInt32BE(4); type = data[9]; if (data[8] !== 8) throw new Error("not 8-bit"); }
    if (kind === "IDAT") idat.push(data);
    pos += 12 + len;
  }
  const bpp = type === 6 ? 4 : type === 2 ? 3 : 0;
  if (!bpp) throw new Error(`PNG colour type ${type}`);
  const raw = inflateSync(Buffer.concat(idat)), stride = width * bpp, out = Buffer.alloc(height * stride);
  for (let y = 0; y < height; y++) {
    const f = raw[y * (stride + 1)], src = raw.subarray(y * (stride + 1) + 1, (y + 1) * (stride + 1));
    for (let x = 0; x < stride; x++) {
      const a = x >= bpp ? out[y * stride + x - bpp] : 0, b = y ? out[(y - 1) * stride + x] : 0, c = x >= bpp && y ? out[(y - 1) * stride + x - bpp] : 0;
      const p = a + b - c, pa = Math.abs(p - a), pb = Math.abs(p - b), pc = Math.abs(p - c);
      const pred = f === 1 ? a : f === 2 ? b : f === 3 ? (a + b) >> 1 : f === 4 ? (pa <= pb && pa <= pc ? a : pb <= pc ? b : c) : 0;
      out[y * stride + x] = (src[x] + pred) & 255;
    }
  }
  return { width, height, rgba: (x, y) => [...out.subarray((y * width + x) * bpp, (y * width + x) * bpp + bpp)] };
}

test("the house renders, the agents change state, notes fly, and nothing leaves localhost", async ({ page, external, shot }) => {
  await open(page, "/");
  await begin(page);
  await nav(page, "Agents").click();
  const house = page.getByRole("group", { name: /The agents' office/ });
  const canvas = house.locator("canvas");
  await expect(canvas).toBeVisible();
  // An agent's label, by the name on its pill (another agent's bubble can say "TO PREPARER").
  const label = (name: string) => house.locator(".agent-house-label").filter({ has: page.locator(".agent-house-pill > b", { hasText: new RegExp(`^${name}$`) }) });
  await expect(label("Mapper")).not.toHaveAttribute("data-state", "idle", { timeout: 20_000 });

  // A real picture: many colours, and most of it not the white background.
  await expect.poll(async () => {
    const img = pixels(await canvas.screenshot());
    const colours = new Set<string>();
    let ink = 0, n = 0;
    for (let y = 0; y < img.height; y += 4) for (let x = 0; x < img.width; x += 4) {
      const [r, g, b] = img.rgba(x, y);
      n += 1;
      if (r < 235 || g < 235 || b < 235) ink += 1;
      colours.add(`${r >> 4},${g >> 4},${b >> 4}`);
    }
    return colours.size >= 40 && ink / n > 0.15;
  }, { timeout: 20_000, message: "the canvas draws the house" }).toBe(true);
  await shot("house-working");

  // States follow the run: the Mapper asks, the controller answers on the Case, the Preparer and Reviewer work.
  await expect(label("Mapper")).toHaveAttribute("data-state", "asking", { timeout: 40_000 });
  const overlay = house.locator(".agent-house-overlay");
  await expect.poll(async () => Number(await overlay.getAttribute("data-notes-sent") ?? 0)).toBeGreaterThan(0);
  await shot("mapper-asking");

  for (let i = 0; i < 2; i++) {
    await nav(page, "Case").click();
    await page.getByRole("main").getByRole("button", { name: /^[a-e]\. .*Suggested/ }).click();
    await expect(page.getByText("Answered").first()).toBeVisible();
  }
  await nav(page, "Agents").click();
  const sent = Number(await overlay.getAttribute("data-notes-sent") ?? 0);
  await expect(label("Preparer")).not.toHaveAttribute("data-state", "idle", { timeout: 30_000 });
  // A note is in the air while the agents hand off.
  await expect.poll(async () => Number(await overlay.getAttribute("data-notes-in-flight") ?? 0), { timeout: 30_000 }).toBeGreaterThan(0);
  await shot("note-in-flight");
  await expect.poll(async () => Number(await overlay.getAttribute("data-notes-sent") ?? 0), { timeout: 30_000 }).toBeGreaterThan(sent);
  await expect(label("Reviewer")).toHaveAttribute("data-state", /working|talking|done/, { timeout: 40_000 });
  await expect(page.getByText("Approve and post")).toBeVisible({ timeout: 40_000 });
  await shot("handed-off");

  expect(external, `requests outside localhost: ${external.join(", ")}`).toEqual([]);
});
