// Reads what the tests need from the exported workbook: each sheet's cells with their fill colour and note.
// The workbook is openpyxl's, so the XML is read directly (a general reader trips on openpyxl's legacy comments).
import fs from "node:fs";
import path from "node:path";
import JSZip from "jszip";

export interface XCell { ref: string; fill: string | null; note: string | null; text: string }
export interface XSheet { name: string; cells: XCell[]; rows: number }

const unescape = (s: string) => s.replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"').replace(/&apos;/g, "'").replace(/&amp;/g, "&");
const attr = (tag: string, name: string) => new RegExp(`\\b${name}="([^"]*)"`).exec(tag)?.[1] ?? null;
const resolve = (from: string, target: string) => (target.startsWith("/") ? target.slice(1) : path.posix.normalize(path.posix.join(path.posix.dirname(from), target)));

async function read(zip: JSZip, name: string): Promise<string> {
  const f = zip.file(name);
  if (!f) throw new Error(`the workbook has no ${name}`);
  return f.async("string");
}

function rels(xml: string, from: string): Map<string, { type: string; target: string }> {
  const out = new Map<string, { type: string; target: string }>();
  for (const m of xml.matchAll(/<Relationship\b[^>]*>/g)) {
    out.set(attr(m[0], "Id")!, { type: attr(m[0], "Type")!, target: resolve(from, attr(m[0], "Target")!) });
  }
  return out;
}

export async function readWorkbook(file: string): Promise<Map<string, XSheet>> {
  const zip = await JSZip.loadAsync(fs.readFileSync(file));
  const strings = [...(await zip.file("xl/sharedStrings.xml")?.async("string") ?? "").matchAll(/<si>([\s\S]*?)<\/si>/g)]
    .map((m) => unescape([...m[1].matchAll(/<t[^>]*>([\s\S]*?)<\/t>/g)].map((t) => t[1]).join("")));
  const styles = await read(zip, "xl/styles.xml");
  const fills = [...(/<fills[^>]*>([\s\S]*?)<\/fills>/.exec(styles)?.[1] ?? "").matchAll(/<fill>([\s\S]*?)<\/fill>/g)]
    .map((m) => /<fgColor\b[^>]*rgb="([0-9A-Fa-f]{6,8})"/.exec(m[1])?.[1]?.slice(-6).toUpperCase() ?? null);
  const xfs = [...(/<cellXfs[^>]*>([\s\S]*?)<\/cellXfs>/.exec(styles)?.[1] ?? "").matchAll(/<xf\b[^>]*>/g)]
    .map((m) => fills[Number(attr(m[0], "fillId") ?? 0)] ?? null);

  const book = await read(zip, "xl/workbook.xml");
  const bookRels = rels(await read(zip, "xl/_rels/workbook.xml.rels"), "xl/workbook.xml");
  const out = new Map<string, XSheet>();
  for (const m of book.matchAll(/<sheet\b[^>]*>/g)) {
    const name = unescape(attr(m[0], "name")!);
    const part = bookRels.get(attr(m[0], "r:id")!)!.target;
    const xml = await read(zip, part);
    const relFile = `${path.posix.dirname(part)}/_rels/${path.posix.basename(part)}.rels`;
    const notes = new Map<string, string>();
    if (zip.file(relFile)) {
      for (const r of rels(await read(zip, relFile), part).values()) {
        if (!r.type.endsWith("/comments")) continue;
        for (const c of (await read(zip, r.target)).matchAll(/<comment\b([^>]*)>([\s\S]*?)<\/comment>/g)) {
          notes.set(attr(c[1], "ref")!, unescape([...c[2].matchAll(/<t[^>]*>([\s\S]*?)<\/t>/g)].map((t) => t[1]).join("")));
        }
      }
    }
    const cells: XCell[] = [];
    for (const c of xml.matchAll(/<c\b([^>]*?)(?:\/>|>([\s\S]*?)<\/c>)/g)) {
      const ref = attr(c[1], "r")!;
      const s = attr(c[1], "s");
      const t = attr(c[1], "t");
      const body = c[2] ?? "";
      const v = /<v>([\s\S]*?)<\/v>/.exec(body)?.[1] ?? /<t[^>]*>([\s\S]*?)<\/t>/.exec(body)?.[1] ?? "";
      const text = t === "s" ? strings[Number(v)] ?? "" : unescape(v);
      cells.push({ ref, fill: s ? xfs[Number(s)] ?? null : null, note: notes.get(ref) ?? null, text });
    }
    out.set(name, { name, cells, rows: new Set(cells.map((c) => /\d+/.exec(c.ref)![0])).size });
  }
  return out;
}
