"""Minimal CLI for AcidEngine — запуск одного скрипта."""
from __future__ import annotations

import sys
import importlib.util
from pathlib import Path

from acid_engine.contracts.conformance import check_conformance, explain_result
from acid_engine.containers.port import PortRef
from acid_engine.containers.snapshot import ContainerSnapshot
from acid_engine.scripts.python_runtime import run_script


def load_script_from_file(path: str):
    """Загружает ScriptModule из Python-файла. Ожидает переменную `script`."""
    spec = importlib.util.spec_from_file_location("user_script", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load script from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "script"):
        raise ValueError(f"Module {path} does not define 'script'")
    return module.script


def main(argv: list[str] | None = None) -> int:
    """Точка входа: python -m acid_engine [script.py] [input_data]"""
    if argv is None:
        argv = sys.argv[1:]

    if len(argv) == 0:
        # Демо-режим: запускаем walking skeleton (x+1)
        from examples.walking_skeleton.run_x_plus_1 import main as ws_main
        ws_main()
        return 0

    script_path = argv[0]
    input_value = int(argv[1]) if len(argv) > 1 else 0

    script = load_script_from_file(script_path)
    in_port = PortRef(module=script.contract_id.name, direction="input", name="value")
    input_snap = ContainerSnapshot.create(
        port_ref=in_port,
        contract_id=script.contract_id,
        contract_hash=script.content_hash,
        data=input_value,
    )

    output_snap, obs, delta, state = run_script(script, input_snap)
    result = check_conformance(
        required_output_type=script.output_type,
        provided_data=output_snap.data,
        obs=obs,
        policy=script.specification.policy,
        node_id=script.name,
        contract_id=str(script.contract_id),
    )

    print(f"Input:  {input_value}")
    print(f"Output: {output_snap.data}")
    print(f"Latency: {obs.latency_ms:.3f} ms")
    print(explain_result(result))

    return 0 if result.ok else 1