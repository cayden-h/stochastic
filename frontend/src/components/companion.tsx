"use client";

/**
 * The companion on the Review page (D19, review-companion.md sections 5 and 6): the Reviewer, a 26 px avatar that
 * trails the cursor, glides to a cell the controller just edited, and asks why. The reason is saved with the edit and
 * the agents learn from it. It lives on the Review page only; no other page has a cursor companion.
 *
 * The follow physics are ported from Squeek's cursor ghost, apps/desktop/src/renderer/halo.js in
 * https://github.com/syedkazmi14/squeek (spring 0.035 toward a hover point, velocity damping 0.76, fixed 60 Hz steps).
 * The look follows the V3-7 Review frames (Figma 670:44) and Josie's Reason popover (545:408).
 */

import { Avatar } from "./ui";
import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";
import { useEdits, type LeverageMove, type PendingConfirm } from "@/lib/edit-context";
import { editAnchor, findAnchor, num, oldestUnreasoned } from "@/lib/edits";
import { fmtX, plural } from "@/lib/format";
import type { Edit, ReasonChip } from "@/lib/types";
import { Arrow } from "./your-edits";

const MARK = 26;          // the Reviewer avatar, as drawn on the frames
const RING = 40;          // its pulse ring while asking
const OFFSET = 49;        // the avatar's centre sits this far below and right of the cursor tip (V3-7.1)
const EDGE = 16;          // it stays this far inside the window
const SPRING = 0.035;     // halo.js
const DAMPING = 0.76;     // halo.js
const STEP = 1000 / 60;   // halo.js: fixed steps, so the feel does not depend on the display's refresh rate
const GLIDE_MS = 250;
const BUBBLE_W = 340;
const SEAT = 12;          // the avatar's centre sits this far right of the cell's edge, on the bubble's tail
const GAP = 28;           // from the cell's edge to the bubble
const TAIL_AT = 112;      // the tail sits this far down the bubble, level with the cell (V3-7.3)
const SHRINK_MS = 200;
const NOTE_GAP = 10;

const reducedQuery = "(prefers-reduced-motion: reduce)";
function subscribeReduced(cb: () => void) {
  const m = window.matchMedia(reducedQuery);
  m.addEventListener("change", cb);
  return () => m.removeEventListener("change", cb);
}
function useReducedMotion(): boolean {
  return useSyncExternalStore(subscribeReduced, () => window.matchMedia(reducedQuery).matches, () => false);
}

type Side = "right" | "below" | "above";
interface Placement { side: Side; left: number; top: number; tail: number; markX: number; markY: number }

const clamp = (v: number, lo: number, hi: number) => Math.min(Math.max(v, lo), Math.max(lo, hi));

/** Where the bubble goes for a cell: to its right if there is room, else below it, else above it.
 * The companion sits on the tail, at the cell's right edge. */
function placeBy(r: DOMRect, bh: number, W: number, H: number): Placement {
  const cy = r.top + r.height / 2;
  if (r.right + GAP + BUBBLE_W <= W - EDGE) {
    const top = clamp(cy - TAIL_AT, EDGE, H - bh - EDGE);
    const tail = clamp(cy - top, 24, bh - 24);
    return { side: "right", left: r.right + GAP, top, tail, markX: r.right + SEAT, markY: cy };
  }
  const left = clamp(r.left, EDGE, W - BUBBLE_W - EDGE);
  const tail = clamp(r.left + Math.min(32, r.width / 2) - left, 24, BUBBLE_W - 24);
  if (r.bottom + GAP + bh <= H - EDGE) {
    return { side: "below", left, top: r.bottom + GAP, tail, markX: left + tail, markY: r.bottom + SEAT };
  }
  const top = Math.max(EDGE, r.top - GAP - bh);
  return { side: "above", left, top, tail, markX: left + tail, markY: r.top - SEAT };
}

/** Bottom-right of the window: where the companion rests with reduced motion. */
function home(W: number, H: number) {
  return { x: W - EDGE - RING / 2, y: H - EDGE - RING / 2 - 40 };
}

/** With reduced motion, or when the cell is not on screen: the bubble opens above the companion at bottom-right. */
function placeHome(bh: number, W: number, H: number): Placement {
  const { x: markX, y: markY } = home(W, H);
  const left = W - EDGE - BUBBLE_W, top = Math.max(EDGE, markY - MARK / 2 - GAP - bh);
  return { side: "above", left, top, tail: clamp(markX - left, 24, BUBBLE_W - 24), markX, markY };
}

function ArrowUp() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
      <path d="M6 9V3M8.7 5.7L6 3L3.3 5.7" stroke="white" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function Tail({ side, at }: { side: Side; at: number }) {
  // A 16 by 22 tail in the bubble's glass, pointing at the cell.
  const fill = "rgba(246,246,245,0.94)";
  if (side === "right") {
    return (
      <svg width="16" height="22" viewBox="0 0 16 22" aria-hidden="true" className="pointer-events-none absolute" style={{ left: -15, top: at - 11 }}>
        <path d="M16 0L1 11L16 22Z" fill={fill} />
      </svg>
    );
  }
  const base = "pointer-events-none absolute size-0 border-solid";
  if (side === "below") {
    return <span className={`${base} border-x-[11px] border-b-[15px] border-x-transparent`} style={{ top: -15, left: at - 11, borderBottomColor: fill }} />;
  }
  return <span className={`${base} border-x-[11px] border-t-[15px] border-x-transparent`} style={{ bottom: -15, left: at - 11, borderTopColor: fill }} />;
}

/** The context lines: the company and line, then what changed and how leverage moved. */
function Context({ edit, company, move }: { edit: Pick<Edit, "kind" | "line" | "old_value" | "new_value" | "old_platform_line" | "new_platform_line">; company: string; move?: LeverageMove }) {
  const crossed = move && move.to >= move.limit && move.from < move.limit;
  const toward = move && move.to > move.from;
  const levTone = crossed ? "text-denied" : toward ? "text-escalation" : "";
  // An unchanged ratio (a remap inside one section) says nothing, so it is left out.
  const moved = move && fmtX(move.from) !== fmtX(move.to) ? move : undefined;
  const lev = moved ? <span className={levTone}>leverage {fmtX(moved.from)} <Arrow /> {fmtX(moved.to)}</span> : null;
  return (
    <>
      <span className="w-full truncate text-[12px] leading-[17px] text-sheet-muted" title={`${company}, ${edit.line}`}>{company} &middot; {edit.line}</span>
      <span className="w-full font-mono text-[11px] leading-[16px] text-bubble-ink">
        {edit.kind === "amount"
          ? <>{num(edit.old_value ?? 0)} <Arrow /> {num(edit.new_value ?? 0)}{lev ? <> &middot; {lev}</> : null}</>
          : <>{edit.old_platform_line ?? "Unmapped"} <Arrow /> {edit.new_platform_line}{lev ? <> &middot; {lev}</> : null}</>}
      </span>
    </>
  );
}

const CHIP = "w-full rounded-[9px] border py-[6px] pr-[4px] pl-[8px] text-left text-[12px] leading-[16px] text-bubble-ink transition-colors duration-150";
const CHIP_OFF = "border-white/80 bg-white/48 hover:bg-white/90";
const CHIP_ON = "border-[rgba(166,166,166,0.65)] bg-[rgba(222,222,222,0.7)]";
const PRIMARY = "rounded-[12px] px-[12px] py-[8px] text-[14px] leading-[20px] whitespace-nowrap text-white transition-colors duration-150";
const LATER = "rounded-[10px] py-[8px] text-[14px] leading-[20px] text-bubble-muted hover:text-ink focus-visible:outline-2 focus-visible:outline-forest";

/** The reason bubble: chips one per row, your own reason, remember, Later and Save. Keys 1 to 3, Enter, Esc, scoped
 * to the bubble: there is no global key handler. */
function ReasonBubble({
  edit, chips, move, company, onLater, onSave, onSaved,
}: {
  edit: Edit; chips: ReasonChip[]; move?: LeverageMove; company: string;
  onLater: () => void; onSave: (r: { chip: number } | { text: string }, remember: boolean) => Promise<Edit>; onSaved: (e: Edit) => void;
}) {
  const [chip, setChip] = useState<number | null>(null);
  const [text, setText] = useState("");
  const [remember, setRemember] = useState(true);
  const [status, setStatus] = useState<"idle" | "saving" | "failed">("idle");
  const ready = (chip !== null || text.trim().length > 0) && status !== "saving";

  const save = async () => {
    if (!ready) return;
    setStatus("saving");
    try {
      const saved = await onSave(chip !== null ? { chip } : { text: text.trim() }, remember);
      onSaved(saved);
    } catch {
      setStatus("failed");
    }
  };

  const onKey = (e: React.KeyboardEvent) => {
    const typing = (e.target as HTMLElement).tagName === "INPUT" && (e.target as HTMLInputElement).type === "text";
    if (e.key === "Escape") { e.preventDefault(); onLater(); return; }
    if (e.key === "Enter") {
      if ((e.target as HTMLElement).dataset.role === "later") return;  // Enter on Later is Later
      e.preventDefault(); void save(); return;
    }
    if (!typing && /^[1-9]$/.test(e.key)) {
      const c = chips[Number(e.key) - 1];
      if (c) { e.preventDefault(); setChip(c.id); setText(""); if (status === "failed") setStatus("idle"); }
    }
  };

  const rememberLabel = edit.kind === "remap" ? "Apply to every add-on on this platform" : "Suggest this on the next add-on";
  return (
    <div onKeyDown={onKey} data-autofocus="" tabIndex={-1} className="flex w-full flex-col items-start gap-[8px] outline-none">
      <h2 id="reason-title" className="font-serif text-[21px] leading-[25px] whitespace-nowrap text-bubble-ink">Why did you make this change?</h2>
      <Context edit={edit} company={company} move={move} />
      <div role="radiogroup" aria-labelledby="reason-title" className="flex w-full flex-col gap-[8px]">
        {chips.map((c, i) => (
          <button
            key={c.id}
            type="button"
            role="radio"
            aria-checked={chip === c.id}
            aria-keyshortcuts={String(i + 1)}
            onClick={() => { setChip(c.id); setText(""); if (status === "failed") setStatus("idle"); }}
            className={`${CHIP} ${chip === c.id ? CHIP_ON : CHIP_OFF}`}
          >
            <span className="font-mono text-[#999]">{i + 1}</span>
            <span className="ml-[6px]">{c.label}</span>
          </button>
        ))}
      </div>
      <label htmlFor="reason-text" className="text-[11px] leading-[15px] text-bubble-ink">Add your reason</label>
      <div className="flex h-[44px] w-full items-center gap-[10px] rounded-[18px] border border-white bg-white/60 py-[7px] pr-[8px] pl-[14px] shadow-[0_5px_8px_rgba(0,0,0,0.06)] focus-within:border-[rgba(166,166,166,0.65)]">
        <input
          id="reason-text"
          type="text"
          value={text}
          maxLength={500}
          placeholder="Type your reason..."
          onChange={(e) => { setText(e.target.value); if (e.target.value) setChip(null); if (status === "failed") setStatus("idle"); }}
          className="min-w-0 flex-1 bg-transparent text-[12px] leading-[18px] text-bubble-ink outline-none placeholder:text-[#737373]"
        />
        <button
          type="button"
          aria-label="Save this reason"
          disabled={!text.trim() || status === "saving"}
          onClick={() => void save()}
          className="flex size-[20px] shrink-0 items-center justify-center rounded-[6px] bg-[#383838] disabled:cursor-default"
        >
          <ArrowUp />
        </button>
      </div>
      <label className="flex w-full cursor-pointer items-center gap-[8px]">
        <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} className="peer sr-only" />
        <span className={`flex size-[18px] shrink-0 items-center justify-center rounded-[4px] peer-focus-visible:outline-2 peer-focus-visible:outline-forest ${remember ? "bg-[#d6d6d6]" : "border border-[#c4c4c4] bg-white/60"}`} aria-hidden="true">
          {remember ? (
            <svg width="13" height="11" viewBox="0 0 13 11" fill="none"><path d="M1.5 5.5L5 9L11.5 1.5" stroke="#6E6E6E" strokeWidth="1.3" strokeLinecap="square" /></svg>
          ) : null}
        </span>
        <span className="text-[11px] leading-[16px] text-bubble-muted">{rememberLabel}</span>
      </label>
      {status === "failed" ? (
        <p role="alert" className="text-[13px] leading-[18px] text-denied">Couldn&apos;t save the reason. Try again.</p>
      ) : null}
      <div className="flex w-full items-start justify-end gap-[8px] pt-[4px]">
        <button type="button" data-role="later" onClick={onLater} className={LATER}>Later</button>
        <button
          type="button"
          disabled={!ready}
          onClick={() => void save()}
          className={`${PRIMARY} ${ready ? "bg-[#383838] hover:bg-ink" : "bg-[#bdbdbd] text-white/70"}`}
        >
          {status === "saving" ? "Saving..." : status === "failed" ? "Retry" : "Save reason"}
        </button>
      </div>
    </div>
  );
}

/** A change of more than half the agents' value asks first, inside the bubble. */
function ConfirmBubble({ pending, company, onYes, onNo }: { pending: PendingConfirm; company: string; onYes: () => void; onNo: () => void }) {
  const [busy, setBusy] = useState(false);
  const yes = () => { if (!busy) { setBusy(true); onYes(); } };
  return (
    <div
      onKeyDown={(e) => {
        if (e.key === "Escape") { e.preventDefault(); onNo(); }
        else if (e.key === "Enter") { e.preventDefault(); if ((e.target as HTMLElement).dataset.role === "change") onNo(); else yes(); }
      }}
      data-autofocus=""
      tabIndex={-1}
      className="flex w-full flex-col items-start gap-[8px] outline-none"
    >
      <h2 className="font-serif text-[21px] leading-[25px] text-bubble-ink">This is a large change.</h2>
      <p className="text-[12px] leading-[17px] text-bubble-ink">Is the amount right? It moves the line by more than half of the agents&apos; value.</p>
      <Context edit={{ kind: "amount", line: pending.body.line, old_value: pending.old, new_value: pending.next, old_platform_line: null, new_platform_line: null }} company={company} />
      <div className="flex w-full items-start justify-end gap-[8px] pt-[4px]">
        <button type="button" data-role="change" onClick={onNo} className={LATER}>Change it</button>
        <button type="button" disabled={busy} onClick={yes} className={`${PRIMARY} ${busy ? "bg-[#bdbdbd] text-white/70" : "bg-[#383838] hover:bg-ink"}`}>
          {busy ? "Saving..." : "Yes, save it"}
        </button>
      </div>
    </div>
  );
}

/** "1 edit needs a reason." or "2 edits need a reason." */
function waitingLabel(n: number): string {
  return `${plural(n, "edit")} ${n === 1 ? "needs" : "need"} a reason.`;
}

/** The Reviewer companion. Pointer-transparent, except for the waiting dot and the bubble. Mounted by the Review page. */
export function Companion() {
  const ctx = useEdits();
  const reduced = useReducedMotion();
  const markRef = useRef<HTMLDivElement>(null);
  const bubbleRef = useRef<HTMLDivElement>(null);
  const noteRef = useRef<HTMLDivElement>(null);
  const [arrived, setArrived] = useState<string | null>(null);  // the anchor the companion has glided to
  const [shrinking, setShrinking] = useState(false);
  const [side, setSide] = useState<{ side: Side; tail: number }>({ side: "right", tail: TAIL_AT });
  // After Save it stays at the cell while the learned note shows, then follows the cursor again.
  const [parked, setParked] = useState<string | null>(null);

  const anchor = ctx.confirm ? ctx.confirm.anchor : ctx.asking ? editAnchor(ctx.asking) : null;
  const waitingEdit = oldestUnreasoned(ctx.edits);
  const waiting = Boolean(waitingEdit) && !anchor;
  const seat = anchor ?? (ctx.note && parked ? parked : null);

  // The loop reads the latest values through refs, so it is set up once.
  const live = useRef({ anchor, seat, reduced, waiting });
  useEffect(() => { live.current = { anchor, seat, reduced, waiting }; }, [anchor, seat, reduced, waiting]);

  useEffect(() => {
    const start = home(window.innerWidth, window.innerHeight);
    const pos = { x: start.x, y: start.y };
    const vel = { x: 0, y: 0 };
    const mouse = { x: pos.x - OFFSET, y: pos.y - OFFSET, outside: false };
    let glide: { key: string; t0: number; fx: number; fy: number } | null = null;
    let placedSide = "";
    let raf = 0, last = performance.now(), acc = 0;

    const onMove = (e: PointerEvent) => { mouse.x = e.clientX; mouse.y = e.clientY; mouse.outside = false; };
    const onLeave = (e: MouseEvent) => { if (!e.relatedTarget) mouse.outside = true; };
    window.addEventListener("pointermove", onMove, { passive: true });
    document.addEventListener("mouseout", onLeave);
    const onBlur = () => { mouse.outside = true; };
    window.addEventListener("blur", onBlur);

    const frame = (now: number) => {
      const { anchor: key, seat: at, reduced: still, waiting: hold } = live.current;
      const W = window.innerWidth, H = window.innerHeight;
      const mark = markRef.current, bubble = bubbleRef.current, note = noteRef.current;
      const bh = bubble?.offsetHeight || 384;
      let opacity = 0.7;
      let place: Placement | null = null;

      if (at) {
        const el = still ? null : findAnchor(at);
        place = el ? placeBy(el.getBoundingClientRect(), bh, W, H) : placeHome(bh, W, H);
        if (!glide || glide.key !== at) glide = { key: at, t0: now, fx: pos.x, fy: pos.y };
        const t = still ? 1 : Math.min(1, (now - glide.t0) / GLIDE_MS);
        const ease = 1 - Math.pow(1 - t, 3);
        pos.x = glide.fx + (place.markX - glide.fx) * ease;
        pos.y = glide.fy + (place.markY - glide.fy) * ease;
        vel.x = vel.y = 0;
        opacity = 1;
        if (key && t >= 1) setArrived((a) => (a === key ? a : key));
        acc = 0;
      } else {
        glide = null;
        setArrived((a) => (a === null ? a : null));
        if (still) {
          const h = home(W, H);
          pos.x = h.x; pos.y = h.y;
        } else {
          acc += Math.min(now - last, 100);
          // Hold still while the cursor reaches for the waiting dot, so it can be clicked.
          const near = hold && Math.hypot(mouse.x - pos.x, mouse.y - pos.y) < 44;
          // Out of the window it parks at the nearest edge, where the cursor left, and dims.
          const tx = clamp(near ? pos.x : mouse.outside ? mouse.x : mouse.x + OFFSET, EDGE + MARK / 2, W - EDGE - MARK / 2);
          const ty = clamp(near ? pos.y : mouse.outside ? mouse.y : mouse.y + OFFSET, EDGE + MARK / 2, H - EDGE - MARK / 2);
          while (acc >= STEP) {
            vel.x = (vel.x + (tx - pos.x) * SPRING) * DAMPING;
            vel.y = (vel.y + (ty - pos.y) * SPRING) * DAMPING;
            pos.x += vel.x; pos.y += vel.y;
            acc -= STEP;
          }
          if (mouse.outside) opacity = 0.4;
        }
      }
      last = now;

      if (mark) {
        mark.style.transform = `translate3d(${pos.x - RING / 2}px, ${pos.y - RING / 2}px, 0)`;
        mark.style.setProperty("--mark-opacity", String(opacity));
      }
      if (bubble && place && key) {
        bubble.style.transform = `translate3d(${place.left}px, ${place.top}px, 0)`;
        const s = `${place.side}:${Math.round(place.tail)}`;
        if (s !== placedSide) { placedSide = s; setSide({ side: place.side, tail: place.tail }); }
      }
      if (note) {
        const w = note.offsetWidth;
        const right = pos.x + MARK / 2 + NOTE_GAP + w <= W - EDGE;
        const nx = right ? pos.x + MARK / 2 + NOTE_GAP : pos.x - MARK / 2 - NOTE_GAP - w;
        note.style.transform = `translate3d(${nx}px, ${pos.y - note.offsetHeight / 2}px, 0)`;
      }
      raf = requestAnimationFrame(frame);
    };
    raf = requestAnimationFrame(frame);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("pointermove", onMove);
      document.removeEventListener("mouseout", onLeave);
      window.removeEventListener("blur", onBlur);
    };
  }, []);

  const open = Boolean(anchor) && arrived === anchor;

  // Focus moves into the bubble when it opens, and back to the cell when it closes.
  const focusBack = useRef<string | null>(null);
  useEffect(() => {
    if (open && bubbleRef.current) {
      focusBack.current = anchor;
      bubbleRef.current.querySelector<HTMLElement>("[data-autofocus]")?.focus({ preventScroll: true });
    } else if (!anchor && focusBack.current) {
      const back = findAnchor(focusBack.current);
      focusBack.current = null;
      if (back && (!document.activeElement || document.activeElement === document.body || bubbleRef.current?.contains(document.activeElement))) {
        back.focus({ preventScroll: true });
      }
    }
  }, [open, anchor]);

  // The parked seat ends with the note.
  const note = ctx.note;
  useEffect(() => {
    if (note) return;
    const t = setTimeout(() => setParked(null), 0);
    return () => clearTimeout(t);
  }, [note]);

  const onSaved = useCallback((saved: Edit) => {
    setShrinking(true);
    setParked(editAnchor(saved));
    setTimeout(() => { setShrinking(false); ctx.finish(saved); }, reduced ? 0 : SHRINK_MS);
  }, [ctx, reduced]);

  const origin = side.side === "right" ? `0 ${side.tail}px` : side.side === "below" ? `${side.tail}px 0` : `${side.tail}px 100%`;
  const unreasoned = ctx.edits.filter((e) => e.status === "needs_reason").length;

  return (
    <div className="pointer-events-none fixed inset-0 z-50 overflow-hidden print:hidden" aria-live="polite">
      {anchor ? (
        <div
          ref={bubbleRef}
          role="dialog"
          aria-modal="false"
          aria-label={ctx.confirm ? "Confirm a large change" : "Why did you make this change?"}
          tabIndex={-1}
          className={`popover-glass pointer-events-auto absolute top-0 left-0 w-[340px] rounded-[20px] px-[20px] pt-[16px] pb-[20px] outline-none transition-[opacity,scale] ease-out ${
            open && !shrinking ? "scale-100 opacity-100 duration-150" : "scale-[0.2] opacity-0 duration-200"
          } ${open ? "" : "invisible"}`}
          style={{ transformOrigin: origin }}
        >
          <Tail side={side.side} at={side.tail} />
          {ctx.confirm ? (
            <ConfirmBubble key={ctx.confirm.anchor} pending={ctx.confirm} company={ctx.confirm.body.company} onYes={() => void ctx.confirmYes()} onNo={ctx.confirmNo} />
          ) : ctx.asking ? (
            <ReasonBubble
              key={ctx.asking.id}
              edit={ctx.asking}
              chips={ctx.chips(ctx.asking.kind)}
              move={ctx.leverage[ctx.asking.id]}
              company={ctx.asking.company}
              onLater={ctx.later}
              onSave={(r, remember) => ctx.save(ctx.asking!, r, remember)}
              onSaved={onSaved}
            />
          ) : null}
        </div>
      ) : null}

      <div
        ref={markRef}
        data-companion={anchor ? "asking" : waiting ? "waiting" : "idle"}
        className="absolute top-0 left-0 size-[40px] will-change-transform"
        aria-hidden={!waiting}
      >
        {anchor ? <span className="companion-pulse absolute inset-0 rounded-full border border-reviewer/22 bg-reviewer-tint/95" aria-hidden="true" /> : null}
        <span className="absolute top-[7px] left-[7px] size-[26px] opacity-[var(--mark-opacity,0.7)] drop-shadow-[0_1px_3px_rgba(64,38,102,0.22)]" aria-hidden="true">
          <Avatar role="reviewer" size={26} className="size-full" />
        </span>
        {waiting && waitingEdit ? (
          <button
            type="button"
            onClick={() => ctx.ask(waitingEdit.id)}
            aria-label={`${waitingLabel(unreasoned)} Give it now.`}
            title="An edit needs a reason. Click to give it."
            className="pointer-events-auto absolute -top-[4px] -right-[4px] flex size-[22px] cursor-pointer items-center justify-center rounded-full focus-visible:outline-2 focus-visible:outline-reviewer"
          >
            <span className="size-[8px] rounded-full bg-reviewer ring-[1.5px] ring-white" />
          </button>
        ) : null}
      </div>

      {note && !anchor ? (
        <div
          ref={noteRef}
          key={note.at}
          role="status"
          className="absolute top-0 left-0 rounded-full border border-[#DCD0EE] bg-white px-[10px] py-[3px] text-[12px] leading-[16px] whitespace-nowrap text-reviewer"
        >
          {note.text}
        </div>
      ) : null}
    </div>
  );
}
