"""Судья — один вход к execute_plan. Тело не пишет закон."""
from __future__ import annotations

from typing import Any

from acid_engine.level2.conformance import ConformanceResult
from acid_engine.level3.bootstrap.plan_lock import PlanLock
from acid_engine.level3.interface.contract import InterfaceContract
from acid_engine.level3.pipeline import PipelineResult
from acid_engine.level3.script.module import ScriptModule
from acid_engine.level3.script.runner import execute_plan

SELF_LOCK_SKIP = "self-lock is not a verdict"


def judge_script(
    script: ScriptModule,
    input_data: Any,
    *,
    plan: PlanLock | None = None,
    iface: InterfaceContract | None = None,
) -> PipelineResult:
    """Вердикт только по паре plan+iface. Self-lock не вердикт. Тело без замка не запускать."""
    from acid_engine.level3.script.resolve import materialize_script

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
    return execute_plan(iface, plan, script, input_data)
