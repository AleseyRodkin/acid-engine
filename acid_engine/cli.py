"""Единый CLI AcidEngine: init, validate, run."""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

from acid_engine.level2.conformance import ConformanceResult, check_conformance, explain_result
from acid_engine.level2.specification import Policy
from acid_engine.level3.script.external_runner import run_external
from acid_engine.level3.script.modes import ExecutionMode
from acid_engine.level3.script.module import ScriptModule


def load_script_from_file(path: str | Path) -> ScriptModule:
    """Load ScriptModule from .py (`script`) or .json blank. Markdown не парсится."""
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"Script file not found: {source}")
    suffix = source.suffix.lower()
    if suffix == ".md":
        raise ValueError("markdown specs are not parsed")
    if suffix == ".json":
        from acid_engine.level2.blank_loader import load_script_blank
        return load_script_blank(source)
    if suffix != ".py":
        raise ValueError(f"Script must be a .py or .json file, got: {source}")
    # unique name so repeated loads do not collide in sys.modules
    mod_name = f"acid_user_script_{source.resolve().stem}_{id(source)}"
    spec = importlib.util.spec_from_file_location(mod_name, str(source))
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {source}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "script"):
        raise ValueError(f"{source} does not define 'script'")
    script = module.script
    if not isinstance(script, ScriptModule):
        raise TypeError(f"{source}: 'script' is {type(script)!r}, expected ScriptModule")
    return script


def parse_cli_input(raw: str | None, default: Any = 3) -> Any:
    """Parse --input: int, JSON (list/dict/...), иначе строка. Без --input → default."""
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def cmd_init(args: argparse.Namespace) -> None:
    """Создаёт шаблон ScriptModule (.py). Markdown-спеки не создаём — не парсятся."""
    target = Path(args.path or "script.py")
    if target.suffix == ".md":
        # старый default был spec.md — не пишем мёртвый markdown
        target = Path("script.py")
        print("NOTE: markdown specs are not parsed; writing script.py instead")

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
    if args.script:
        target = Path(args.script)
    target.write_text(script_content, encoding="utf-8")
    print(f"Script created: {target}")


def cmd_validate(args: argparse.Namespace) -> None:
    """Проверка внешней команды по .py-контракту (переменная contract)."""
    spec_path = Path(args.spec)
    if not spec_path.exists():
        print(f"ERROR: spec file not found: {spec_path}")
        sys.exit(1)
    if spec_path.suffix != ".py":
        print(
            "ERROR: markdown specs are not parsed. "
            "Pass a .py file that defines 'contract'."
        )
        sys.exit(1)

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


def cmd_lock(args: argparse.Namespace) -> None:
    """Заморозить plan.lock текущего тела в JSON. Не вердикт."""
    try:
        script = load_script_from_file(args.script)
    except Exception as e:
        print(f"ERROR: Failed to load script: {e}")
        sys.exit(1)
    from acid_engine.level3.script.runner import dump_script_lock

    payload = dump_script_lock(script)
    out = Path(args.out)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"plan.lock written: {out}")
    print(f"plan.lock: {payload['interface_contract_hash'][:16]}...")


def cmd_run(args: argparse.Namespace) -> None:
    """Walking skeleton или пользовательский скрипт через judge_script."""
    if args.script:
        try:
            script = load_script_from_file(args.script)
        except Exception as e:
            print(f"ERROR: Failed to load script: {e}")
            sys.exit(1)
        input_val = parse_cli_input(args.input, default=3)
        from acid_engine.judge import judge_script
        from acid_engine.level3.pipeline import PipelineResult
        from acid_engine.level3.script.runner import load_script_lock

        if not args.plan:
            skipped = ConformanceResult.skipped(
                "CLI run --script without --plan is not a verdict (self-lock is tautology)"
            )
            result = PipelineResult(conformance=skipped)
            print(explain_result(result.conformance))
            _maybe_write_receipt(args, script, input_val, result, plan=None)
            sys.exit(1)
        try:
            raw = json.loads(Path(args.plan).read_text(encoding="utf-8"))
            iface, plan = load_script_lock(raw)
        except Exception as e:
            print(f"ERROR: Failed to load plan: {e}")
            sys.exit(1)
        result = judge_script(script, input_val, plan=plan, iface=iface)
        print(explain_result(result.conformance))
        print(f"output: {result.data}")
        print(f"plan.lock: {plan.content_hash[:16]}...")
        _maybe_write_receipt(args, script, input_val, result, plan=plan)
        if not result.ok:
            sys.exit(1)
    else:
        from examples.walking_skeleton.run_x_plus_1 import main as ws_main
        ws_main()


def _maybe_write_receipt(
    args: argparse.Namespace,
    script: Any,
    input_val: Any,
    result: Any,
    plan: Any,
) -> None:
    path = getattr(args, "receipt", None)
    if not path:
        return
    from acid_engine.receipt import build_receipt, write_receipt

    payload = build_receipt(script, input_val, result, plan=plan)
    write_receipt(path, payload)
    print(f"receipt: {path}")


def cmd_judge(args: argparse.Namespace) -> None:
    """Публичный вход: bind до run + вердикт. То же, что run --script --plan."""
    if not args.script:
        print("ERROR: lock not passed — judge requires --script")
        sys.exit(1)
    cmd_run(args)


def _add_script_plan_input(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--script", help="Путь к .py (переменная script) или .json blank")
    parser.add_argument(
        "--plan",
        help="JSON plan.lock (acid_engine lock --script). Без него SKIPPED",
    )
    parser.add_argument(
        "--input",
        help="Вход: int, JSON (напр. '[1,2,3]') или строка. По умолчанию 3",
    )
    parser.add_argument(
        "--receipt",
        help="Куда писать receipt.json (факт + вердикт, без proven_pure)",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="acid-engine",
        description="Acid Judge: lock, judge, receipt.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_init = subparsers.add_parser("init", help="Создать шаблон ScriptModule (.py)")
    p_init.add_argument("--path", default="script.py", help="Путь к .py файлу скрипта")
    p_init.add_argument("--script", help="Альтернативный путь к шаблону скрипта")
    p_init.set_defaults(func=cmd_init)

    p_val = subparsers.add_parser("validate", help="Проверить внешнюю команду по контракту")
    p_val.add_argument("spec", help="Путь к .py файлу с переменной contract")
    p_val.add_argument("command", nargs="*", help="Команда для проверки")
    p_val.set_defaults(func=cmd_validate)

    p_run = subparsers.add_parser("run", help="Скрипт через plan.lock или walking skeleton")
    _add_script_plan_input(p_run)
    p_run.set_defaults(func=cmd_run)

    p_judge = subparsers.add_parser(
        "judge",
        help="Bind plan.lock до run + вердикт (алиас run --script --plan)",
    )
    _add_script_plan_input(p_judge)
    p_judge.set_defaults(func=cmd_judge)

    p_lock = subparsers.add_parser("lock", help="Замок на тело (JSON plan.lock)")
    p_lock.add_argument("--script", required=True, help="Путь к .py или .json blank")
    p_lock.add_argument("--out", required=True, help="Куда писать JSON замка")
    p_lock.set_defaults(func=cmd_lock)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
