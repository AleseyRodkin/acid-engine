# AcidEngine — состояние

**Репозиторий:** https://github.com/AleseyRodkin/acid-engine-2.0
Закон: METHOD.md. Очередь: PLAN.md.

## Снимок 31.08.2026

Сборка из zip `8e1b2a7`. Фазы 1–6 закрыты. Аудит-фиксы после фазы 6.

## Сделано

1–21. Контур до `judge_script` (хеш тела, SKIPPED, plan.lock, bones, JSON blank).
22. Аудит: plan+iface вместе; obs.status в gate; Composite внешний lock;
    нет fallback одного хеша; replay_from_record требует plan; resolve один раз.

Не делать: Rust без команды, STOL, SaaS, веб-превью ядра.
