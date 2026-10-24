"""The credit agreement as text: normalization, the hash, and the section and definition indexes (D20).

Pure functions, no store. The gateway checks the Brief Reader's quotes with them, and the job runner builds the
reader's input with them. Rules are in docs/architecture/brief-reader.md sections 5 and 6.
"""
from __future__ import annotations

import hashlib
import math
import re

MIN_QUOTE_WORDS = 4
PREAMBLE = "preamble"

_STRAIGHT = str.maketrans({"“": '"', "”": '"', "„": '"', "‘": "'", "’": "'",
                           " ": " ", " ": " ", " ": " "})


def normalize(text: str) -> str:
    """Both sides of every quote check: curly quotes made straight, non-breaking spaces made spaces, the ` | ` cell
    separators of scripts/fetch_filings.py removed, whitespace collapsed. Nothing fuzzier, so "4.50" never matches
    "4.25" and a "not" is never dropped."""
    text = text.translate(_STRAIGHT)
    text = re.sub(r"\s\|\s", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def agreement_sha256(text: str) -> str:
    """The key an approved Brief is stored under: the hash of the normalized text, so the same agreement fetched
    twice (or saved with other line endings) is the same agreement, and an amendment is a new one."""
    return hashlib.sha256(normalize(text).encode()).hexdigest()


def quote_in(quote: str, text: str) -> bool:
    """A quote counts if, normalized, it is an exact substring of the normalized text and at least four words."""
    q = normalize(quote)
    return len(q.split()) >= MIN_QUOTE_WORDS and q in normalize(text)


# ---------------------------------------------------------------------------- sections and definitions

_NUMBERED = re.compile(r"^(\d+(?:\.\d+)*)\.\s+(\S.*)$")  # "4.8. Financial Covenants ."
# "Section 7.1 Leverage Ratio" or "SECTION 7.1.": the number ends the line, takes a dot, or is followed by a capital.
# A wrapped cross-reference ("Section 5.8 ." or "Section 6 of this Agreement") is not a heading.
_SECTION = re.compile(r"^(?i:section)\s+(\d+(?:\.\d+)*)(?:\.|\s+([A-Z][A-Za-z].*))?$")
_DOTTED = re.compile(r"^(\d+\.\d+(?:\.\d+)*)\s+([A-Z][A-Za-z].*)$")  # "7.1 Leverage Ratio": a dotted number, a title
_LETTERED = re.compile(r"^\(([a-z])\)\s*(.*)$")
_ANNEX = re.compile(r"^(ADDENDUM|ANNEX|EXHIBIT|SCHEDULE)\s+([A-Z]|[IVX]+|\d+)$", re.I)  # alone on its line
_DEFINED = re.compile(r'"\s*([^"]{1,80}?)\s*"\s+(?:shall\s+)?means?\b')


def _heading(rest: str) -> str:
    title = rest.split(" . ")[0].split(". ")[0]
    return normalize(title)[:80]


def sections(text: str) -> list[tuple[str, str, int, int]]:
    """(id, heading, start line, end line) for each section, in order. Ids: `preamble`, `4.8`, `4.8(a)`,
    `Addendum I`. A lettered subsection belongs to the numbered section above it."""
    lines = text.splitlines()
    marks: list[tuple[str, str, int, int]] = []  # id, heading, line, level (0 annex, 1 numbered, 2 lettered)
    current = None
    for i, raw in enumerate(lines):
        row = normalize(raw)
        if m := _ANNEX.match(row):
            sid = f"{m.group(1).title()} {m.group(2)}"
            marks.append((sid, sid, i, 0))
            current = None
        elif m := (_SECTION.match(row) or _NUMBERED.match(row) or _DOTTED.match(row)):
            current = m.group(1)
            marks.append((current, _heading(m.group(2) or "") or f"Section {current}", i, 1))
        elif current and (m := _LETTERED.match(row)):
            marks.append((f"{current}({m.group(1)})", _heading(m.group(2)) or f"({m.group(1)})", i, 2))
    out: list[tuple[str, str, int, int]] = []
    first = marks[0][2] if marks else len(lines)
    if first > 0:
        out.append((PREAMBLE, "Preamble", 0, first))
    for n, (sid, head, start, level) in enumerate(marks):
        end = len(lines)
        for sid2, _, start2, level2 in marks[n + 1:]:
            if level2 <= level or (level == 1 and level2 == 0):
                end = start2
                break
        out.append((sid, head, start, end))
    return out


def section_index(text: str) -> dict[str, str]:
    return {sid: head for sid, head, _, _ in sections(text)}


def section_text(text: str, section_id: str) -> str | None:
    lines = text.splitlines()
    for sid, _, start, end in sections(text):
        if sid == section_id:
            return "\n".join(lines[start:end])
    return None


def _definitions(text: str) -> list[tuple[str, str, int]]:
    """(term, section id, character offset in the normalized text) for each `"X" means` or `"X" shall mean`."""
    out = []
    spans = sections(text)
    lines = text.splitlines()
    for sid, _, start, end in spans:
        body = normalize("\n".join(lines[start:end]))
        for m in _DEFINED.finditer(body):
            out.append((normalize(m.group(1)), sid, m.start()))
    return out


def definition_index(text: str) -> dict[str, str]:
    """Defined term -> the section that defines it. The first definition of a term wins."""
    index: dict[str, str] = {}
    for term, sid, _ in _definitions(text):
        index.setdefault(term, sid)
    return index


def definition_text(text: str, term: str, limit: int = 3000) -> str | None:
    """The definition of a term: from its opening quote to the next definition in the same section."""
    defs = _definitions(text)
    key = normalize(term).casefold()
    for n, (t, sid, at) in enumerate(defs):
        if t.casefold() != key:
            continue
        body = normalize(section_text(text, sid) or "")
        start = body.rfind('"', 0, body.find(t, at) + 1)
        nxt = next((a for t2, s2, a in defs[n + 1:] if s2 == sid), len(body))
        return body[max(start, at):nxt].strip()[:limit]
    return None


LEVERAGE = re.compile(r"\bto\s+EBITDA\b|leverage\s+ratio|funded\s+debt", re.I)


def leverage_excerpts(text: str, max_chars: int = 6000) -> dict[str, str]:
    """The numbered and lettered sections that mention a leverage ratio, each at most `max_chars`. Annexes (the
    definitions) are left out: the reader asks for a definition by name with get_definition."""
    out = {}
    for sid, _, _, _ in sections(text):
        if sid == PREAMBLE or not sid[0].isdigit():
            continue
        body = normalize(section_text(text, sid) or "")
        if len(body) <= max_chars and (LEVERAGE.search(body) or any(
                LEVERAGE.search(normalize(section_text(text, child) or "")) for child, _, _, _ in sections(text)
                if child.startswith(sid + "("))):
            out[sid] = body
    # A lettered subsection whose numbered section is included is left out, so no text is given twice. The whole
    # numbered section is kept, so the reader also sees the covenants next to the leverage test.
    return {sid: body for sid, body in out.items() if "(" not in sid or sid.split("(")[0] not in out}


# ---------------------------------------------------------------------------- numbers in quotes

def _forms_of_ratio(x: float) -> set[str]:
    return {f"{x:.2f}", f"{x:.1f}", f"{x:g}"}


def ratio_in(quote: str, x: float) -> bool:
    q = normalize(quote)
    return any(re.search(rf"(?<![\d.]){re.escape(f)}(?![\d])", q) for f in _forms_of_ratio(x))


def thousands_in(quote: str, amount_k: float) -> bool:
    """A cap in USD thousands appears in its quote after the unit conversion: 4000 as "$4,000,000", "4,000,000",
    or "$4 million"."""
    if not math.isfinite(amount_k):
        return False
    q = normalize(quote)
    dollars = amount_k * 1000
    forms = {f"{dollars:,.0f}", f"{dollars:,.2f}"}
    if dollars >= 1_000_000:
        forms |= {f"{dollars / 1_000_000:g} million", f"{dollars / 1_000_000:.1f} million"}
    return any(re.search(rf"(?<![\d,.]){re.escape(f)}(?![\d])", q) for f in forms)
