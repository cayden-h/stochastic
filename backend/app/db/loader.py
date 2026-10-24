"""Strict loader for uploaded statement CSVs. Untrusted input: validate every row before building any line.

A bad file raises LoaderError naming the row (1-based, the header is row 1) and the column. It never half-loads.
"""
from __future__ import annotations

import csv
import io
import math
from typing import Callable

from app.core.models import SourceLine
from app.tools import finance

MAX_ROWS = 2000
MAX_BYTES = 2 * 1024 * 1024

REQUIRED = ["line", "section", "period", "amount", "unit", "source_ref", "is_total"]
SECTIONS = ("income_statement", "balance_sheet", "cash_flow")
TAGS = ("debt", "not_debt", "unclear", "na")
BOOLS = {"true": True, "1": True, "yes": True, "false": False, "0": False, "no": False, "": False}


class LoaderError(ValueError):
    pass


def _parse_amount(raw: str) -> float:
    s = raw.strip().replace(",", "").strip()
    negative = s.startswith("(") and s.endswith(")")
    if negative:
        s = s[1:-1].strip()
    value = float(s)  # ValueError on junk
    if not math.isfinite(value):
        raise ValueError("not finite")
    return -value if negative else value


def parse_statement_csv(text: str, company: str, deal_id: str, next_id: Callable[[str], str]) -> list[SourceLine]:
    reader = csv.reader(io.StringIO(text, newline=""))
    try:
        header = next(reader, None)
    except csv.Error as error:
        raise LoaderError(f"row 1: unreadable CSV ({error})")
    if header is None:
        raise LoaderError("row 1: file is empty, header required")
    header = [h.strip().lstrip("﻿").lower() for h in header]
    for col in REQUIRED:
        if col not in header:
            raise LoaderError(f"row 1, column {col}: required column is missing")
    idx = {name: header.index(name) for name in REQUIRED + ["covenant_tag"] if name in header}

    parsed: list[dict] = []
    try:
        for n, row in enumerate(reader, start=2):
            if not row or all(not c.strip() for c in row):
                continue
            if len(parsed) >= MAX_ROWS:
                raise LoaderError(f"row {n}: more than {MAX_ROWS} data rows")
            if len(row) < len(REQUIRED) and len(row) <= max(idx[c] for c in REQUIRED):
                raise LoaderError(f"row {n}: expected {len(REQUIRED)} columns, found {len(row)}")

            def cell(col: str) -> str:
                i = idx[col]
                return row[i] if i < len(row) else ""

            line = cell("line").strip()
            if not line or len(line) > 200:
                raise LoaderError(f"row {n}, column line: must be 1 to 200 characters")
            section = cell("section").strip()
            if section not in SECTIONS:
                raise LoaderError(f"row {n}, column section: '{section[:40]}' is not one of {', '.join(SECTIONS)}")
            period = cell("period").strip()
            if not period or len(period) > 64:
                raise LoaderError(f"row {n}, column period: must be 1 to 64 characters")
            try:
                amount = _parse_amount(cell("amount"))
            except ValueError:
                raise LoaderError(f"row {n}, column amount: '{cell('amount')[:40]}' is not a finite number")
            unit = cell("unit").strip()
            try:
                finance.to_thousands(0.0, unit)
            except ValueError:
                raise LoaderError(f"row {n}, column unit: unknown unit '{unit[:40]}'")
            source_ref = cell("source_ref").strip()
            if len(source_ref) > 500:
                raise LoaderError(f"row {n}, column source_ref: longer than 500 characters")
            flag = cell("is_total").strip().lower()
            if flag not in BOOLS:
                raise LoaderError(f"row {n}, column is_total: '{flag[:20]}' is not true, false, 1, 0, yes, or no")
            tag = "na"
            if "covenant_tag" in idx:
                tag = cell("covenant_tag").strip().lower() or "na"
                if tag not in TAGS:
                    raise LoaderError(f"row {n}, column covenant_tag: '{tag[:20]}' is not one of {', '.join(TAGS)}")
            parsed.append(dict(line=line, section=section, period=period, amount=amount, unit=unit,
                               source_ref=source_ref, is_total=BOOLS[flag], covenant_tag=tag))
    except csv.Error as error:
        raise LoaderError(f"unreadable CSV ({error})")
    if not parsed:
        raise LoaderError("no data rows found")
    return [SourceLine(id=next_id("sl"), deal_id=deal_id, company=company, **p) for p in parsed]
