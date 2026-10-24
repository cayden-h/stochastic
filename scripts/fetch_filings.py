"""Download the Kewaunee and Nu Aire filings from SEC EDGAR into data/raw/ and write a plain-text copy of each.

    python3 scripts/fetch_filings.py

Needs SEC_USER_AGENT in .env (a real contact email; SEC rule). Skips files already cached.
data/ is git-ignored: the SEC redistribution wording is unresolved, so the cache stays local.
"""
from __future__ import annotations

import html
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
BASE = "https://www.sec.gov/Archives/edgar/data/55529"

# name -> (EDGAR path, what it is). Links match docs/research/real-deal-candidates.md.
FILINGS = {
    "10q_2024-10-31": ("000005552924000040/kequ-20241031.htm", "Kewaunee 10-Q, quarter ended 2024-10-31"),
    "10k_fy2024": ("000005552924000021/kequ-20240430.htm", "Kewaunee 10-K, year ended 2024-04-30"),
    "8ka_ex99-1": ("000119312525007212/d915304dex991.htm", "8-K/A Ex 99.1, Nu Aire audited statements"),
    "8ka_ex99-2": ("000119312525007212/d915304dex992.htm", "8-K/A Ex 99.2, pro forma combined"),
    "8k_ex10-1": ("000119312524249232/d886750dex101.htm", "8-K Ex 10.1, PNC Loan Agreement"),
}


def user_agent() -> str:
    env = ROOT / ".env"
    if env.exists():
        for row in env.read_text().splitlines():
            if row.startswith("SEC_USER_AGENT="):
                os.environ.setdefault("SEC_USER_AGENT", row.split("=", 1)[1].strip().strip('"'))
    ua = os.environ.get("SEC_USER_AGENT", "")
    if "@" not in ua or "example.com" in ua:
        sys.exit("Set SEC_USER_AGENT in .env to a name and a real contact email.")
    return ua


def to_text(page: str) -> str:
    page = re.sub(r"(?is)<(script|style).*?</\1>", " ", page)
    page = re.sub(r"(?i)<(br|/p|/div|/tr|/h\d)[^>]*>", "\n", page)
    page = re.sub(r"(?i)</t[dh]>", " | ", page)
    page = html.unescape(re.sub(r"<[^>]+>", " ", page)).replace("\xa0", " ")
    lines = (re.sub(r"[ \t]+", " ", row).strip(" |") for row in page.splitlines())
    return "\n".join(row for row in lines if row)


def main() -> int:
    ua = user_agent()
    RAW.mkdir(parents=True, exist_ok=True)
    for name, (path, label) in FILINGS.items():
        dest = RAW / f"{name}.htm"
        if not dest.exists():
            req = urllib.request.Request(f"{BASE}/{path}", headers={"User-Agent": ua})
            with urllib.request.urlopen(req, timeout=60) as resp:
                dest.write_bytes(resp.read())
            time.sleep(0.2)  # stay well under the SEC's 10 requests per second
        (RAW / f"{name}.txt").write_text(to_text(dest.read_text(errors="replace")))
        print(f"{name}: {label} ({dest.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
