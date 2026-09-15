"""Судья — один вход к execute_plan. Тело не пишет закон."""
from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from acid_engine.level2.conformance import ConformanceResult
from acid_engine.level3.bootstrap.plan_lock import PlanLock
from acid_engine.level3.interface.contract import InterfaceContract
from acid_engine.level3.pipeline import PipelineResult
from acid_engine.level3.script.module import ScriptModule
from acid_engine.level3.script.runner import execute_plan

SELF_LOCK_SKIP = "self-lock is not a verdict"
RUNTIME_UNPINNED = "runtime not pinned"


def judge_script(
    script: ScriptModule,
    input_data: Any,
    *,
    plan: PlanLock | None = None,
    iface: InterfaceContract | None = None,
    toolchain: Mapping[str, Any] | None = None,
) -> PipelineResult:
    """Вердикт только по паре plan+iface и пину контура. Self-lock не вердикт."""
    from acid_engine.level2.implementation_canon import live_canon_kind
    from acid_engine.level3.script.resolve import materialize_script
    from acid_engine.worker import verify_runtime_pin

    script = materialize_script(script)
    if plan is None and iface is None:
        return PipelineResult(
            conformance=ConformanceResult.skipped(SELF_LOCK_SKIP),
        )
    if plan is None or iface is None:
        return PipelineResult(
            conformance=ConformanceResult.skipped(
                "plan and iface must be provided together"
            )
        )
    if toolchain is None:
        return PipelineResult(
            conformance=ConformanceResult.skipped(RUNTIME_UNPINNED),
        )
    pin = verify_runtime_pin(
        toolchain, live_canon_kind=live_canon_kind(script.implementation)
    )
    if pin is not None:
        return PipelineResult(conformance=pin)
    return execute_plan(iface, plan, script, input_data, toolchain=toolchain)


def judge_script_from_lock(
    script: ScriptModule,
    input_data: Any,
    lock_path: str | Path,
) -> PipelineResult:
    """Читает plan+iface+toolchain из JSON замка. Безопасный путь — самый простой."""
    from acid_engine.level3.script.runner import load_script_lock

    raw = json.loads(Path(lock_path).read_text(encoding="utf-8"))
    iface, plan = load_script_lock(raw)
    return judge_script(script, input_data, plan=plan, iface=iface, toolchain=raw)
