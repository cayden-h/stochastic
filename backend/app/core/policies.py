"""Which learned policy covers which line. One rule, used by the gateway and by the scripted Mapper.

A company policy (a flag answer, D18) applies to its own company's lines only; a policy with no company applies to
nothing. A platform policy (a remap edit, D19) applies only as a mapping, and only to the target lines of a deal
whose platform is the one it names. Company and platform names are compared casefolded and stripped.
When several live policies cover a line, the newest wins, so a later correction beats an earlier answer.
"""
from __future__ import annotations

from collections.abc import Iterable

from app.core.models import Policy


def same_name(a: str | None, b: str | None) -> bool:
    return a is not None and b is not None and a.strip().casefold() == b.strip().casefold()


def policy_applies(p: Policy, company: str, platform: str, target: str) -> bool:
    if p.retired_by:
        return False
    if p.scope == "platform":
        return p.kind == "mapping" and same_name(p.platform, platform) and same_name(company, target)
    return same_name(p.company, company)


def newest_covering(policies: Iterable[Policy], kind: str, pattern: str, company: str, platform: str,
                    target: str) -> Policy | None:
    """The newest live policy of this kind on this line name whose scope covers the line."""
    hits = [p for p in policies if p.kind == kind and p.pattern == pattern
            and policy_applies(p, company, platform, target)]
    return max(hits, key=lambda p: p.at) if hits else None
