"""Python worker for the external judge. Runs a body. Does not verdict."""
from __future__ import annotations

import json
import sys
from typing import Any

from acid_engine.cli import load_script_from_file
from acid_engine.level3.container.port import PortRef
from acid_engine.level3.container.snapshot import ContainerSnapshot
from acid_engine.level3.script.module import ScriptModule
from acid_engine.level3.script.python_runtime import run_script
from acid_engine.level3.script.resolve import materialize_script


def identify_script(script: ScriptModule) -> dict[str, Any]:
    policy = script.specification.policy
    return {
        "script_name": script.name or script.contract_id.name,
        "script_hash": script.content_hash,
        "contract_id": str(script.contract_id),
        "output_type": script.output_type,
        "input_type": script.input_type,
        "pure": bool(getattr(policy, "pure", False)),
    }


def run_body(script: ScriptModule, input_data: Any) -> dict[str, Any]:
    in_port = PortRef(module=script.contract_id.name, direction="input", name="value")
    snap = ContainerSnapshot.create(
        port_ref=in_port,
        contract_id=script.contract_id,
        contract_hash=script.content_hash,
        data=input_data,
    )
    out, obs, _delta, _state = run_script(script, snap)
    payload = identify_script(script)
    payload["data"] = out.data
    payload["effects"] = list(obs.effects_observed)
    payload["observation"] = {
        "status": obs.status,
        "latency_ms": obs.latency_ms,
        "effects_observed": list(obs.effects_observed),
        "trace": list(obs.trace),
        "input_hash": obs.input_hash,
        "output_hash": obs.output_hash,
    }
    return payload


def handle(req: dict[str, Any]) -> dict[str, Any]:
    op = str(req.get("op") or "")
    script_path = req.get("script")
    if not script_path:
        raise ValueError("worker request needs script path")
    script = materialize_script(load_script_from_file(str(script_path)))
    if op == "identify":
        return identify_script(script)
    if op == "run":
        return run_body(script, req.get("input"))
    raise ValueError(f"unknown worker op: {op!r}")


def main() -> None:
    raw = sys.stdin.read()
    try:
        req = json.loads(raw) if raw.strip() else {}
        if not isinstance(req, dict):
            raise ValueError("worker stdin must be a JSON object")
        out = handle(req)
    except Exception as e:
        sys.stderr.write(f"ERROR: {e}\n")
        sys.exit(2)
    sys.stdout.write(json.dumps(out, ensure_ascii=False))
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
