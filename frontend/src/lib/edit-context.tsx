"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { api } from "./api";
import { useDeal } from "./deal-context";
import { DEMO_CHIPS, editAnchor, findAnchor, isLargeChange, learnedNote, liveEdits } from "./edits";
import type { Edit, EditBody, ReasonChip } from "./types";

/** A large change waits in the bubble for a yes before it is sent. */
export interface PendingConfirm { body: EditBody; anchor: string; old: number; next: number }

/** The leverage before and after an edit, from the verdict on screen and the edit's recompute. */
export interface LeverageMove { from: number; to: number; limit: number }

interface EditData {
  /** The live edits, newest last. */
  edits: Edit[];
  chips: (kind: Edit["kind"]) => ReasonChip[];
  leverage: Record<string, LeverageMove>;
  /** The edit whose reason bubble is open. */
  asking: Edit | null;
  confirm: PendingConfirm | null;
  /** The one-line note after Save, shown beside the companion for 4 s. */
  note: { text: string; at: number } | null;
  /** True while an edit is recomputed and the Reviewer's checks re-run (at least a second, so it can be read). */
  rechecking: boolean;
  /** The cell being typed in, by anchor key. One at a time. */
  editing: string | null;
  setEditing: (key: string | null) => void;
  /** The cell that flashes after a Your edits row is clicked. */
  flash: { key: string; at: number } | null;
  error: string | null;
  clearError: () => void;
  clearNote: () => void;
  /** Send an edit. A change over half the agents' value asks in the bubble first, unless `confirmed`. */
  apply: (body: EditBody, anchor: string, old?: number, confirmed?: boolean) => Promise<boolean>;
  confirmYes: () => Promise<void>;
  confirmNo: () => void;
  ask: (id: string) => void;
  later: () => void;
  /** Save the reason. Throws on failure so the bubble can show its failed state; the bubble stays open. */
  save: (edit: Edit, reason: { chip: number } | { text: string }, remember: boolean) => Promise<Edit>;
  /** After the bubble has shrunk into the companion: close it and show the learned note. */
  finish: (saved: Edit) => void;
  revert: (id: string) => Promise<void>;
  /** Scroll to the edited cell and flash it. */
  show: (id: string) => void;
}

const Ctx = createContext<EditData | null>(null);
const RECHECK_MS = 1000;
const NOTE_MS = 4000;

/** The review edits (D19): the controller changes the books, the companion asks why, the agents learn.
 * The console still computes no figure: every number on screen comes back from the gateway's recompute. */
export function EditProvider({ children }: { children: React.ReactNode }) {
  const { kase, refresh, audit } = useDeal();
  // Edits the gateway returned this session, by id. Until T2 adds `edits` to /case they are the only record, so an
  // edit left for Later stays on screen; once /case carries edits, its copy wins by id.
  const [local, setLocal] = useState<Record<string, Edit>>({});
  const edits = useMemo(() => {
    const byId = new Map(Object.values(local).filter((e) => e.deal_id === kase?.deal.id).map((e) => [e.id, e]));
    for (const e of kase?.edits ?? []) byId.set(e.id, e);
    return liveEdits(kase ? { ...kase, edits: [...byId.values()] } : null).sort((a, b) => a.at.localeCompare(b.at));
  }, [kase, local]);
  const remember = (e: Edit) => setLocal((m) => ({ ...m, [e.id]: e }));
  const [chipCache, setChipCache] = useState<Partial<Record<Edit["kind"], ReasonChip[]>>>({});
  const [leverage, setLeverage] = useState<Record<string, LeverageMove>>({});
  const [askingId, setAskingId] = useState<string | null>(null);
  const [confirm, setConfirm] = useState<PendingConfirm | null>(null);
  const [note, setNote] = useState<{ text: string; at: number } | null>(null);
  const [rechecking, setRechecking] = useState(false);
  const [editing, setEditing] = useState<string | null>(null);
  const [flash, setFlash] = useState<{ key: string; at: number } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const dealId = kase?.deal.id;
  // A reset reseeds the ledger: the deal's first audit row changes, so what this session held is dropped.
  const ledger = `${dealId ?? ""}|${audit.rows[0]?.hash ?? ""}`;
  const verdictRef = useRef(kase?.verdict ?? null);
  useEffect(() => { verdictRef.current = kase?.verdict ?? null; }, [kase]);

  const asking = askingId ? edits.find((e) => e.id === askingId) ?? null : null;

  // The chips: from /case when T2 sends them, else the last edit's response, else the demo deal's list.
  const caseChips = kase?.reason_chips;
  const chips = useCallback((kind: Edit["kind"]) => caseChips?.[kind] ?? chipCache[kind] ?? DEMO_CHIPS[kind], [caseChips, chipCache]);

  const send = useCallback(async (body: EditBody): Promise<boolean> => {
    if (!dealId) return false;
    setError(null); setRechecking(true);
    const started = Date.now();
    const before = verdictRef.current;
    try {
      const res = await api.edit(dealId, body);
      setChipCache((c) => ({ ...c, [res.edit.kind]: res.reasons }));
      if (before) setLeverage((l) => ({ ...l, [res.edit.id]: { from: before.leverage, to: res.verdict.leverage, limit: res.verdict.limit } }));
      remember(res.edit);
      await refresh();
      setEditing(null);
      // The companion glides to the cell and opens the bubble.
      setAskingId(res.edit.id);
      return true;
    } catch (e) {
      setError(e instanceof Error ? e.message : "The edit was not saved.");
      return false;
    } finally {
      const left = RECHECK_MS - (Date.now() - started);
      if (left > 0) setTimeout(() => setRechecking(false), left); else setRechecking(false);
    }
  }, [dealId, refresh]);

  const apply = useCallback(async (body: EditBody, anchor: string, old?: number, confirmed = false) => {
    if (body.kind === "amount" && old != null && !confirmed) {
      if (isLargeChange(old, body.value)) {
        setEditing(null);
        setConfirm({ body, anchor, old, next: body.value });
        return true;
      }
    }
    return send(body);
  }, [send]);

  const confirmYes = useCallback(async () => {
    if (!confirm) return;
    const c = confirm;
    setConfirm(null);
    await send(c.body);
  }, [confirm, send]);

  const confirmNo = useCallback(() => {
    if (!confirm) return;
    setEditing(confirm.anchor);  // back to the cell, to fix the amount
    setConfirm(null);
  }, [confirm]);

  const clearNote = useCallback(() => setNote(null), []);
  const ask = useCallback((id: string) => { setConfirm(null); setAskingId(id); }, []);
  const later = useCallback(() => setAskingId(null), []);

  const save = useCallback(async (edit: Edit, reason: { chip: number } | { text: string }, remember: boolean) => {
    const saved = await api.reason(edit.id, reason, remember);
    setLocal((m) => ({ ...m, [saved.id]: saved }));
    void refresh();  // the cell turns to "reason given" while the bubble shrinks
    return saved;
  }, [refresh]);

  const finish = useCallback((saved: Edit) => {
    setAskingId(null);
    setNote({ text: learnedNote(saved.kind, saved.reason_text ?? "", saved.remember), at: Date.now() });
  }, []);

  useEffect(() => {
    if (!flash) return;
    const t = setTimeout(() => setFlash(null), 1200);
    return () => clearTimeout(t);
  }, [flash]);

  useEffect(() => {
    if (!note) return;
    const t = setTimeout(() => setNote(null), NOTE_MS);
    return () => clearTimeout(t);
  }, [note]);

  const revert = useCallback(async (id: string) => {
    setError(null); setRechecking(true);
    const started = Date.now();
    try {
      const res = await api.revert(id);
      remember(res.edit);
      if (askingId === id) setAskingId(null);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "The edit was not undone.");
    } finally {
      const left = RECHECK_MS - (Date.now() - started);
      if (left > 0) setTimeout(() => setRechecking(false), left); else setRechecking(false);
    }
  }, [askingId, refresh]);

  const show = useCallback((id: string) => {
    const e = edits.find((x) => x.id === id);
    if (!e) return;
    const key = editAnchor(e);
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    findAnchor(key)?.scrollIntoView({ block: "center", behavior: reduce ? "auto" : "smooth" });
    setFlash({ key, at: Date.now() });
  }, [edits]);

  // A deal switch or a reset closes whatever was open and drops what this session held for the old ledger.
  useEffect(() => {
    const t = setTimeout(() => {
      setAskingId(null); setConfirm(null); setEditing(null); setLocal({}); setLeverage({}); setNote(null);
    }, 0);
    return () => clearTimeout(t);
  }, [ledger]);

  const value: EditData = {
    edits, chips, leverage, asking, confirm, note, rechecking, editing, setEditing, flash, error,
    clearError: () => setError(null), clearNote, apply, confirmYes, confirmNo, ask, later, save, finish, revert, show,
  };
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useEdits(): EditData {
  const v = useContext(Ctx);
  if (!v) throw new Error("useEdits must be used inside EditProvider");
  return v;
}
