"""Единый CLI AcidEngine: init, validate, run."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from acid_engine.level2.conformance import check_conformance, explain_result
from acid_engine.level3.script.external_runner import run_external
from acid_engine.level3.script.modes import ExecutionMode
from acid_engine.level2.specification import Policy
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level3.interface.contract import InterfaceContract


def cmd_init(args):
    """Создаёт шаблон спецификации (OpenSpec) и простой скрипт."""
    spec_content = """# demo-contract
## Scenario: echo returns expected output
- **GIVEN** input: "hello"
- **WHEN** the echo command is executed
- **THEN** stdout contains hello
"""
    spec_path = Path(args.path or "spec.md")
    spec_path.write_text(spec_content, encoding="utf-8")
    print(f"Spec created: {spec_path}")

    if args.script:
        script_content = '''"""Demo script for AcidEngine."""
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Specification, Policy
from acid_engine.level3.script.module import ScriptModule

script = ScriptModule(
    contract_id=ContractId(namespace="demo", name="my_script"),
    version=Version(0, 1, 0),
    specification=Specification(
        policy=Policy(pure=True, max_latency_ms=100),
    ),
    input_type="int",
    output_type="int",
    implementation=lambda x: x + 1,
    name="demo_script",
)
'''
        script_path = Path(args.script)
        script_path.write_text(script_content, encoding="utf-8")
        print(f"Script created: {script_path}")


def cmd_validate(args):
    """Запускает проверку контракта для внешней команды."""
    spec_path = Path(args.spec)
    if not spec_path.exists():
        print(f"ERROR: spec file not found: {spec_path}")
        sys.exit(1)

    # Пробуем загрузить контракт как Python-модуль (ожидаем переменную contract)
    try:
        from acid_engine.level2.loader import PythonLoader
        loader = PythonLoader()
        if loader.can_load(spec_path):
            iface = loader.load(spec_path)
        else:
            raise ValueError("Not a valid Python contract file")
    except Exception as e:
        print(f"ERROR: Failed to load contract: {e}")
        sys.exit(1)

    command = args.command if args.command else ["echo", "hello"]
    out_snap, obs, delta, state = run_external(
        command=command,
        contract_id=iface.contract_id,
        contract_hash=iface.content_hash,
        mode=ExecutionMode.NORMAL,
    )

    policy = Policy(
        max_latency_ms=iface.constraints.get("max_latency_ms"),
        pure=iface.constraints.get("pure", False),
    )

    result = check_conformance(
        required_output_type="dict",
        provided_data=out_snap.data,
        obs=obs,
        policy=policy,
        node_id=command[0],
        contract_id=str(iface.contract_id),
        semantic_rules=iface.constraints.get("semantic_rules"),
    )

    print(explain_result(result))
    if not result.ok:
        sys.exit(1)


def cmd_run(args):
    """Запускает walking skeleton или пользовательский скрипт."""
    if args.script:
        from acid_engine.cli import load_script_from_file as _load
        script = _load(args.script)
        input_val = int(args.input) if args.input else 3
        from acid_engine.level3.container.port import PortRef
        from acid_engine.level3.container.snapshot import ContainerSnapshot
        from acid_engine.level3.script.python_runtime import run_script

        in_port = PortRef(module=script.contract_id.name, direction="input", name="value")
        input_snap = ContainerSnapshot.create(
            port_ref=in_port,
            contract_id=script.contract_id,
            contract_hash=script.content_hash,
            data=input_val,
        )
        out_snap, obs, delta, state = run_script(script, input_snap)
        result = check_conformance(
            required_output_type=script.output_type,
            provided_data=out_snap.data,
            obs=obs,
            policy=script.specification.policy,
            node_id=script.name,
            contract_id=str(script.contract_id),
        )
        print(explain_result(result))
    else:
        # Демо: walking skeleton
        from examples.walking_skeleton.run_x_plus_1 import main as ws_main
        ws_main()


def main():
    parser = argparse.ArgumentParser(prog="acid-engine", description="AcidEngine CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # init
    p_init = subparsers.add_parser("init", help="Создать шаблон спецификации")
    p_init.add_argument("--path", default="spec.md", help="Путь к файлу спеки")
    p_init.add_argument("--script", help="Создать шаблон скрипта")
    p_init.set_defaults(func=cmd_init)

    # validate
    p_val = subparsers.add_parser("validate", help="Проверить внешнюю команду по спецификации")
    p_val.add_argument("spec", help="Путь к spec.md")
    p_val.add_argument("command", nargs="*", help="Команда для проверки")
    p_val.set_defaults(func=cmd_validate)

    # run
    p_run = subparsers.add_parser("run", help="Запустить скрипт или walking skeleton")
    p_run.add_argument("--script", help="Путь к Python-файлу со скриптом")
    p_run.add_argument("--input", help="Входное значение (для int-скриптов)")
    p_run.set_defaults(func=cmd_run)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()