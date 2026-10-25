// Run with `npm run test:lib` (node --test; Node strips the types).
import assert from "node:assert/strict";
import { test } from "node:test";
import {
  type ConversationMessage, type ConversationState, type MappingEvent,
  TALK_MS, agentStates, conversationReducer, emptyConversation, emptyMappings, liveList, mappingReducer,
  mergeMappings, nextTalkEnd, openQuestions, readyForApproval,
} from "../conversation.ts";

const D = "d_kequ_nuaire";
let n = 0;
function msg(from: string, to: string, kind: string, text = "", item_id: string | null = null, at?: string): ConversationMessage {
  n += 1;
  return { id: `msg_${String(n).padStart(3, "0")}`, deal_id: D, at: at ?? `2026-10-24T10:00:${String(n).padStart(2, "0")}Z`, from, to, kind, text, item_id, run_id: null, line_id: null };
}
function feed(msgs: ConversationMessage[], receivedAt = 0, start: ConversationState = emptyConversation): ConversationState {
  return msgs.reduce((s, m) => conversationReducer(s, { type: "message", message: m, receivedAt }), start);
}

/** The demo deal's run, as the scripted backend writes it (measured 2026-10-24). */
function demoRun(): ConversationMessage[] {
  n = 0;
  return [
    msg("system:gateway", "agent:mapper", "handoff", "Map the 53 lines", "wi_001"),
    msg("agent:mapper", "system:gateway", "message", "Proposing 53 mappings", "wi_001"),
    msg("system:gateway", "agent:mapper", "check", "Checked and accepted", "wi_001"),
    msg("agent:mapper", "human:controller", "question", "Which parts count?", "wi_002"),
    msg("agent:mapper", "human:controller", "question", "Where does it belong?", "wi_003"),
    msg("human:controller", "agent:mapper", "answer", "Option b", "wi_002"),
    msg("system:gateway", "agent:mapper", "message", "Learned 5 policies", "wi_002"),
    msg("human:controller", "agent:mapper", "answer", "Option a", "wi_003"),
    msg("agent:mapper", "agent:preparer", "handoff", "Mappings posted", "wi_004"),
    msg("system:gateway", "agent:preparer", "message", "leverage: 0.76x"),
    msg("agent:preparer", "agent:reviewer", "handoff", "Draft books ready", "wi_005"),
    msg("agent:reviewer", "agent:preparer", "check", "Tie-out passes", "wi_005"),
    msg("agent:reviewer", "human:controller", "handoff", "Ready for your approval", "wi_006"),
  ];
}

test("messages stay in order and a replayed message is not added twice", () => {
  const run = demoRun();
  let s = feed(run.slice(0, 5));
  s = feed(run.slice(0, 5), 0, s); // the stream replays history on reconnect
  assert.deepEqual(s.messages.map((m) => m.id), ["msg_001", "msg_002", "msg_003", "msg_004", "msg_005"]);
  // Out of order arrival is sorted by the id's number.
  const t = feed([run[2], run[0], run[1]]);
  assert.deepEqual(t.messages.map((m) => m.id), ["msg_001", "msg_002", "msg_003"]);
});

test("a held id that comes back with another time means a reset: the list starts over", () => {
  const run = demoRun();
  const s = feed(run);
  const again = { ...run[0], at: "2026-10-24T11:00:00Z" };
  const t = conversationReducer(s, { type: "message", message: again, receivedAt: 5 });
  assert.equal(t.messages.length, 1);
  assert.equal(t.messages[0].at, again.at);
  assert.equal(conversationReducer(s, { type: "reset" }).messages.length, 0);
});

test("a message for another deal starts the list over", () => {
  const run = demoRun();
  const s = feed(run.slice(0, 3));
  const other = { ...run[0], deal_id: "d_other" };
  const t = conversationReducer(s, { type: "message", message: other, receivedAt: 0 });
  assert.equal(t.deal, "d_other");
  assert.equal(t.messages.length, 1);
});

test("a load merges with what the stream already delivered, and an empty or conflicting load replaces it", () => {
  const run = demoRun();
  const s = feed(run.slice(0, 6), 100);
  const t = conversationReducer(s, { type: "load", deal: D, messages: run.slice(0, 4) });
  assert.equal(t.messages.length, 6);
  assert.equal(t.received.msg_005, 100);
  const empty = conversationReducer(s, { type: "load", deal: D, messages: [] });
  assert.equal(empty.messages.length, 0);
  const fresh = conversationReducer(s, { type: "load", deal: D, messages: [{ ...run[0], at: "2026-10-24T12:00:00Z" }] });
  assert.equal(fresh.messages.length, 1);
});

test("the agents' states follow the rules through the demo run", () => {
  const run = demoRun();
  const at = (k: number) => agentStates(feed(run.slice(0, k)), 1e12);
  assert.equal(at(0).mapper.state, "idle");
  assert.equal(at(1).mapper.state, "working"); // handoff to the Mapper
  assert.equal(at(4).mapper.state, "asking");  // a question to the controller
  assert.deepEqual(at(5).mapper.waitingOn, ["wi_002", "wi_003"]);
  assert.equal(at(6).mapper.state, "asking");  // one answer of two: still asking
  assert.deepEqual(at(6).mapper.waitingOn, ["wi_003"]);
  assert.equal(at(8).mapper.state, "working"); // both answered
  assert.equal(at(9).mapper.state, "done");    // handed off
  assert.equal(at(9).preparer.state, "working");
  assert.equal(at(11).preparer.state, "done");
  assert.equal(at(11).reviewer.state, "working");
  const end = at(13);
  assert.equal(end.reviewer.state, "done");    // "Ready for your approval"
  assert.equal(end["brief-reader"].state, "idle");
});

test("an agent talks for TALK_MS after a message this page received, then works again; history never talks", () => {
  const run = demoRun();
  const live = feed(run.slice(0, 2), 1000);
  assert.equal(agentStates(live, 1000 + 10).mapper.state, "talking");
  assert.equal(agentStates(live, 1000 + TALK_MS + 1).mapper.state, "working");
  assert.equal(nextTalkEnd(live, 1000 + 10), 1000 + TALK_MS);
  assert.equal(nextTalkEnd(live, 1000 + TALK_MS + 1), null);
  const loaded = conversationReducer(emptyConversation, { type: "load", deal: D, messages: run.slice(0, 2) });
  assert.equal(agentStates(loaded, 0).mapper.state, "working");
});

test("open questions and the Reviewer's hand-off", () => {
  const run = demoRun();
  assert.deepEqual(openQuestions(feed(run.slice(0, 5))).map((m) => m.item_id), ["wi_002", "wi_003"]);
  assert.deepEqual(openQuestions(feed(run.slice(0, 6))).map((m) => m.item_id), ["wi_003"]);
  assert.equal(openQuestions(feed(run)).length, 0);
  assert.equal(readyForApproval(feed(run.slice(0, 12))), null);
  assert.equal(readyForApproval(feed(run))?.id, "msg_013");
  // A later question from the Reviewer (needs attention) takes the hand-off back.
  const later = feed([...run, msg("agent:reviewer", "human:controller", "question", "Tie-out fails", "wi_007")]);
  assert.equal(readyForApproval(later), null);
  assert.equal(agentStates(later, 1e12).reviewer.state, "asking");
});

function mapping(id: string, extra: Partial<MappingEvent> = {}): MappingEvent {
  return {
    mapping_id: id, line_id: `sl_${id}`, company: "Nu Aire", section: "balance_sheet", line: `Line ${id}`,
    platform_line: "Cash", platform_line_id: "sl_001", confidence: 0.9, reason: "Same line", flagged: false,
    approved_by: null, policy_id: null, at: "2026-10-24T10:00:00Z", ...extra,
  };
}

test("mappings upsert by id and keep the first-stored order", () => {
  let s = emptyMappings;
  for (const id of ["m_001", "m_002", "m_003"]) s = mappingReducer(s, { type: "upsert", deal: D, mapping: mapping(id), receivedAt: 1 });
  s = mappingReducer(s, { type: "upsert", deal: D, mapping: mapping("m_002", { approved_by: "human:controller", platform_line: "Other" }), receivedAt: 2 });
  assert.deepEqual(s.order, ["m_001", "m_002", "m_003"]);
  assert.equal(s.byId.m_002.platform_line, "Other");
  assert.equal(s.received.m_002, 2);
  // The same mapping again changes nothing.
  assert.equal(mappingReducer(s, { type: "upsert", deal: D, mapping: s.byId.m_001, receivedAt: 9 }), s);
  // Another deal starts over; a reset empties.
  assert.equal(mappingReducer(s, { type: "upsert", deal: "d_other", mapping: mapping("m_009"), receivedAt: 3 }).order.length, 1);
  assert.equal(liveList(mappingReducer(s, { type: "reset" })).length, 0);
});

test("merged mappings: live ones first, then case-only ones", () => {
  let s = emptyMappings;
  s = mappingReducer(s, { type: "upsert", deal: D, mapping: mapping("m_002"), receivedAt: 1 });
  const caseRows = [mapping("m_001"), mapping("m_002", { platform_line: "Stale" })].map((e) => ({
    id: e.mapping_id, target_line_id: e.line_id, platform_line_id: e.platform_line_id, target_line: e.line,
    platform_line: e.platform_line, confidence: e.confidence, reason: e.reason, flagged: e.flagged,
    approved_by: e.approved_by, policy_id: e.policy_id,
  }));
  const merged = mergeMappings(caseRows, s);
  assert.deepEqual(merged.map((m) => m.id), ["m_002", "m_001"]);
  assert.equal(merged[0].platform_line, "Cash");
  assert.equal(mergeMappings(caseRows, emptyMappings), caseRows);
});
