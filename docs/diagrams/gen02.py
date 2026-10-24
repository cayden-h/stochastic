# Generates 02-deal-flowgraph.html (page 1 swimlane is computed so the arrows line up with the boxes)
W, H = 158, 128
cx = [222 + 196 * i for i in range(7)]
lane_top = [44, 240, 436]
node_top = [t + 34 for t in lane_top]
phases = ["1 START", "2 READ", "3 FIND LIMITS", "4 DESIGN", "5 TEST", "6 DECIDE", "7 CLOSE"]

human = [
    ("", [], "Upload + brief", "Documents plus one line: amount, purpose, limits."),
    ("", ["E1", "E2"], "Missing docs? Facts?", "Add missing documents. Fix wrong facts."),
    ("", ["E3"], "Unclear clause?", "Answers when a clause or term is unclear."),
    ("", ["E4"], "Plan blocked", "Sees the clause, the redesign, and the consent route."),
    ("", ["E5"], "Best plan flips?", "Reviews what changed after an event."),
    ("", ["E6"], "Final call", "Approve, reject (next page), or ask for changes."),
    ("", [], "Approved", "The reviewer signs off."),
]
agents = [
    ("Deal manager", "Names the situation, picks a playbook, makes the tasks."),
    ("Intake agent", "Turns documents into facts with page and quote."),
    ("Clause reader", "Finds baskets, covenants, definitions. Exact quotes."),
    ("Structuring agent", "Proposes senior, junior, and preferred mixes."),
    ("Risk agent", "Chooses scenarios and explains the results."),
    ("Memo agent", "Writes the recommendation and side-by-side table."),
    None,
]
code = [
    ("Gateway", "Creates the deal. Logs every action."),
    ("Fact store", "Saves facts and citations in Postgres."),
    ("Quote check", "Rejects a quote that is not in the document."),
    ("Deal math", "Computes leverage and cost. Keeps the best trade-offs."),
    ("Monte Carlo", "Seeded run on the shortlist. Returns a run id."),
    ("Gateway checks", "Proposer cannot approve. Every number has a run id."),
    ("POSTED", "Written to the record. Audit log closed."),
]

out = []
# lanes
lane_cls = [("var(--human-soft)", "HUMAN<br>REVIEWER"), ("var(--agent-soft)", "AI<br>AGENTS"), ("var(--code-soft)", "CODE<br>(NO AI)")]
for i, (bg, label) in enumerate(lane_cls):
    out.append(f'<div style="position:absolute;left:0;top:{lane_top[i]}px;width:1520px;height:196px;background:{bg};border-top:2px solid #0b0f1a;{"border-bottom:2px solid #0b0f1a;" if i == 2 else ""}"></div>')
    out.append(f'<div style="position:absolute;left:14px;top:{lane_top[i] + 70}px;width:96px;font-family:\'Press Start 2P\',monospace;font-size:11px;line-height:1.5;">{label}</div>')
# phase headers
for i, p in enumerate(phases):
    out.append(f'<div style="position:absolute;left:{cx[i] - 85}px;top:8px;width:170px;height:28px;border:2.5px solid #0b0f1a;border-radius:8px;background:#fff;font-weight:800;font-size:12.5px;letter-spacing:.05em;display:flex;align-items:center;justify-content:center;">{p}</div>')

def node(i, lane, cls, title, desc, badges=()):
    b = "".join(f'<span class="badge">{x}</span>' for x in badges)
    b = f"<div>{b}</div>" if b else ""
    return (f'<div class="n {cls}" style="left:{cx[i] - W // 2}px;top:{node_top[lane]}px;width:{W}px;height:{H}px;">{b}<h3>{title}</h3><p>{desc}</p></div>')

for i, (_, bd, t, d) in enumerate(human):
    if i == 6:
        out.append(f'<div class="n human" style="left:{cx[i] - W // 2}px;top:{node_top[0] + 24}px;width:{W}px;height:80px;border-radius:40px;text-align:center;"><h3 style="margin-top:8px">{t}</h3><p>{d}</p></div>')
    else:
        out.append(node(i, 0, "human", t, d, bd))
for i, a in enumerate(agents):
    if a:
        out.append(node(i, 1, "agent", a[0], a[1]))
for i, c in enumerate(code):
    if i == 6:
        out.append(f'<div class="n code" style="left:{cx[i] - W // 2}px;top:{node_top[2]}px;width:{W}px;height:{H}px;border-color:#0a7d5c;border-width:4px;"><h3>{c[0]}</h3><p>{c[1]}</p></div>')
    else:
        out.append(node(i, 2, "code", c[0], c[1]))

# arrows
arr = []
def line(x1, y1, x2, y2, color="#0b0f1a", dash=False, both=False, w=3.5):
    d = ' stroke-dasharray="7 5"' if dash else ""
    m = {"#0b0f1a": "aN", "#e5173f": "aR", "#0a7d5c": "aG"}[color]
    ms = f' marker-start="url(#{m})"' if both else ""
    arr.append(f'<path d="M{x1} {y1} L{x2} {y2}" stroke="{color}" stroke-width="{w}" fill="none"{d}{ms} marker-end="url(#{m})"/>')

ay = node_top[1] + H // 2
hy = node_top[0] + H // 2
cy = node_top[2] + H // 2
# agent chain
for i in range(5):
    line(cx[i] + W // 2 + 2, ay, cx[i + 1] - W // 2 - 3, ay)
# human to agent (col 0 single down navy, cols 1-5 red dashed both)
line(cx[0], node_top[0] + H + 2, cx[0], node_top[1] - 3)
for i in range(1, 6):
    line(cx[i], node_top[0] + H + 3, cx[i], node_top[1] - 4, "#e5173f", True, True)
# agent to code
line(cx[0], node_top[1] + H + 2, cx[0], node_top[2] - 3)
for i in range(1, 6):
    line(cx[i], node_top[1] + H + 3, cx[i], node_top[2] - 4, both=True)
# human lane 6 -> 7 (approve) and code 6 -> 7 (post)
line(cx[5] + W // 2 + 2, hy, cx[6] - W // 2 - 3, hy, "#0a7d5c")
line(cx[5] + W // 2 + 2, cy, cx[6] - W // 2 - 3, cy, "#0a7d5c")
# approved -> posted, passes through empty agent lane
line(cx[6], node_top[0] + 24 + 80 + 2, cx[6], node_top[2] - 3, "#0a7d5c")

labels = [
    (cx[5] + W // 2 - 14, hy - 40, "approve"),
    (cx[6] + 8, node_top[1] + 52, "record it"),
]
lab = "".join(f'<div class="lbl" style="left:{x}px;top:{y}px;font-size:11.5px;padding:2px 6px;">{t}</div>' for x, y, t in labels)

strip = ('<div style="position:absolute;left:24px;top:642px;width:1472px;height:48px;background:#101a3a;color:#fff;border:3px solid #0b0f1a;border-radius:12px;'
         'display:flex;align-items:center;gap:14px;padding:0 16px;font-size:14px;font-weight:600;">'
         '<b style="font-family:\'Press Start 2P\',monospace;font-size:11px;color:#ffd23f;font-weight:400;white-space:nowrap;flex:none;">ANY TIME</b>'
         '<span>An event can arrive: a rate move, a lender change, or a late document. The deal manager marks the affected results <b>stale</b> and re-runs only those steps. If the best plan changes, <b style="color:#ffd23f">E5</b> asks the reviewer.</span></div>')

svg = ('<svg class="arrows" viewBox="0 0 1520 700"><defs>'
       '<marker id="aN" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#0b0f1a"/></marker>'
       '<marker id="aR" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#e5173f"/></marker>'
       '<marker id="aG" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#0a7d5c"/></marker>'
       '</defs>' + "".join(arr) + '</svg>')

page1 = "\n    ".join(out) + "\n    " + svg + "\n    " + lab + "\n    " + strip
tpl = open("02-template.html").read()
open("02-deal-flowgraph.html", "w").write(tpl.replace("<!--SWIMLANE-->", page1))
print("ok", len(page1))
