"""Which facts a verdict had. Not a risk score."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from acid_engine.level2.conformance import ConformanceResult, ConformanceStatus


def missing_evidence(
    result: ConformanceResult | Any,
    *,
    plan: Any | None = None,
    toolchain: Mapping[str, Any] | None = None,
) -> list[str]:
    """Facts that were not present. Empty on PASS and on FAIL (enough to decide)."""
    conf = result.conformance if hasattr(result, "conformance") else result
    if conf.status != ConformanceStatus.SKIPPED:
        return []
    msg = conf.message.lower()
    missing: list[str] = []
    if "self-lock" in msg or "plan and iface" in msg:
        missing.append("lock")
    if "runtime not pinned" in msg:
        missing.append("runtime_pin")
    if "no module_hashes" in msg or "no module hash" in msg:
        missing.append("body_bind")
    if "execution was skipped" in msg or "no observation" in msg:
        missing.append("observation")
    if not missing:
        if plan is None:
            missing.append("lock")
        if toolchain is None:
            missing.append("runtime_pin")
    seen: set[str] = set()
    out: list[str] = []
    for item in missing:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out or ["insufficient_facts"]


def evidence_block(missing: list[str]) -> dict[str, Any]:
    return {"missing": missing}
