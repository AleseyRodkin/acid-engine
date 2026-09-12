# AcidEngine — состояние

**Репозиторий:** https://github.com/AleseyRodkin/acid-engine-2.0
Закон: METHOD.md. Очередь костей: PLAN.md. Очередь продукта: COMMERCIAL.md.

## Снимок 12.09.2026

Сборка 0.2: одно лицо Acid Judge. Не zip `8e1b2a7`.

## Сделано

1–21. Контур до `judge_script` (хеш тела, SKIPPED, plan.lock, bones, JSON blank).
22. Аудит: plan+iface вместе; obs.status в gate; Composite внешний lock.
23. Один канон хеша после materialize; CompositeResult.conformance — вердикт графа.
24. `rust/acid-judge` bind → python worker → verdict. Без worker SKIPPED.
25. Identity: ArtifactRef не в хеше. CLI `run --script` без `--plan` → SKIPPED.
26. `container_blank` несёт data; примеры сами находят корень репо; ARCHITECTURE — архив, не план.
27. Worker: `acid_engine.worker` identify/run, без PASS/FAIL.
28. Канон AST — `unparse`. Витринный `n_plus_one.plan.json` = живое тело.
    cargo ≥ 1.75, lockfile v3. Rust verdict: type/status/pure/latency.
29. C0: README Acid Judge; CLI `judge` = `run --script --plan`. Receipt нет.
30. C1: `acid_engine/receipt.py`, `judge --receipt`. Без proven_pure.
31. C2: `locks/index.json` + `.github/workflows/acid-judge.yml`. Без plan не судит.
32. C3: пять tools в `examples/tools/` + plan.json; индекс bones+tools.
33. C4: Claude Code PreToolUse, только bind. MCP нет. Pre не PASS.
34. C5: `acid_engine locks --index`. Сверка тела с замком, не исполнение.
35. C6: Ed25519 на каноне receipt. `receipt --verify`. Не Sigstore.
36. C7: API=CLI. `judge_script` / Pipeline без plan+iface → SKIPPED. Self-lock не вердикт.
37. H1–H5: бинарь без worker → SKIPPED. Observation без worker не вердикт.
38. 0.2: ARCHITECTURE в `docs/archive/`. Threat model на витрине. `acid-judge` — supervisor, не второй канон.
    CI: pytest 3.11/3.12 + locks + cargo. `toolchain` в JSON замка рядом с identity, не в хеше.
39. Три разреза: property без hypothesis — skip; `init`/`validate` скрыты из `--help`; supervisor пинит SHA-256 `worker.py` до identify.
40. Контур рантайма: `runtime_hashes` на `worker.py` + `python_runtime.py` + `runner.py` + `implementation_canon.py`. `locks --index` без пина → FAIL.
41. `judge_script` без `toolchain` → SKIPPED. Неполный пин → FAIL. `judge_script_from_lock` читает JSON замка.
42. Витрина: фраза рынка (не MCP-gateway), [ATTACK.md](ATTACK.md), ярусы в COMMERCIAL без ценников. Второй hook не начат.
43. `toolchain.canon` = `python.ast.v1` рядом с identity. `level0`/`level4`/`services` в `research/`, import path тот же.
44. Витрина: trust continuity. FAIL говорит «не запускали». `diff` — inspection, не вердикт. MCP и capability не начаты.

Фазы 1–6 закрыты. Фаза 7: `rust/acid-judge` supervisor: bind → python worker → verdict.
Без worker — SKIPPED. Worker не пишет вердикт. Хеш тела — только Python canon.

Не делать: STOL, JS/WASM, proven_pure, SaaS, markdown parser, веб-превью ядра.
