"""Судья — один вход к execute_plan. Тело не пишет закон."""
from __future__ import annotations

from typing import Any, Optional

from acid_engine.level3.bootstrap.plan_lock import PlanLock
from acid_engine.level3.interface.contract import InterfaceContract
from acid_engine.level3.pipeline import PipelineResult
from acid_engine.level3.script.module import ScriptModule
from acid_engine.level3.script.runner import execute_plan, lock_for_script


def judge_script(
    script: ScriptModule,
    input_data: Any,
    *,
    plan: Optional[PlanLock] = None,
    iface: Optional[InterfaceContract] = None,
) -> PipelineResult:
    """Вердикт по скрипту. Без plan — замок на текущее тело, затем bind до run."""
    if plan is None or iface is None:
        iface, plan = lock_for_script(script)
    return execute_plan(iface, plan, script, input_data)
