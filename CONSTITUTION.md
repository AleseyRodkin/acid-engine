# AcidEngine — состояние

**Репозиторий:** https://github.com/AleseyRodkin/acid-engine-2.0
Закон: METHOD.md. Очередь: PLAN.md.

## Снимок 31.08.2026

Сборка из zip `8e1b2a7`. Фазы 1–6 закрыты. Аудит-фиксы после фазы 6.

## Сделано

1–21. Контур до `judge_script` (хеш тела, SKIPPED, plan.lock, bones, JSON blank).
22. Аудит: plan+iface вместе; obs.status в gate; Composite внешний lock.
23. Один канон хеша после materialize; CompositeResult.conformance — вердикт графа.
24. `rust/acid-judge` bind → python worker → verdict. Зеркало без worker.
25. Identity: ArtifactRef не в хеше. CLI `run --script` без `--plan` → SKIPPED.
26. `container_blank` несёт data; примеры сами находят корень репо; ARCHITECTURE помечен как не план.
27. Worker: `acid_engine.worker` identify/run, без PASS/FAIL.

Фазы 1–6 закрыты. Фаза 7: `rust/acid-judge` bind → python worker → verdict.
Без worker — зеркало observation. Worker не пишет вердикт.

Не делать: STOL, JS/WASM, proven_pure, SaaS, markdown parser, веб-превью ядра.
