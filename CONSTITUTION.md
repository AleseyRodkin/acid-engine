# AcidEngine — состояние

**Репозиторий:** https://github.com/AleseyRodkin/acid-engine-2.0
Закон: METHOD.md. Очередь: PLAN.md.

## Снимок 31.08.2026

Сборка из zip `8e1b2a7`. Фазы 1–6 закрыты. Аудит-фиксы после фазы 6.

## Сделано

1–21. Контур до `judge_script` (хеш тела, SKIPPED, plan.lock, bones, JSON blank).
22. Аудит: plan+iface вместе; obs.status в gate; Composite внешний lock.
23. Один канон хеша после materialize; CompositeResult.conformance — вердикт графа.
24. `rust/acid-judge` bind+verdict (зеркало, не worker).
25. Identity: ArtifactRef не в хеше. CLI `run --script` без `--plan` → SKIPPED.

Фазы 1–6 закрыты. Фаза 7 не закрыта: бинарник не запускает Python-рабочего
и не является арбитром снаружи процесса.

Не делать: STOL, JS/WASM, proven_pure, SaaS, markdown parser, веб-превью ядра.
