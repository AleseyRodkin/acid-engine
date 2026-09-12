# Acid Judge — коммерческий план для сборщика

**Дата:** 12.09.2026  
Закон только [METHOD.md](METHOD.md). [PLAN.md](PLAN.md) (кости 0.1) не переоткрывать.  
База: снимок `c72ea42`. Если нет `worker.py` / `lock` / `--plan` — сначала актуальный zip.

Курс: личный эксперимент достигнут. Дальше — ниша fail-closed gate тела tool. STOL не стенд.

## 1. Что продаём

Продукт: **Acid Judge** (не зонтик AcidEngine, не PyPI-ренейм).  
Фраза: file-byte lock on a locally approved Python tool body, checked immediately before the agent call.  
Не MCP-gateway: шлюз ловит отравленные *описания* tool на сети; этот gate ловит подмену *файла* между одобрением и вызовом. Дополнение, не конкурент шлюзу.

Покупатель: Head of Platform / AppSec / AI Governance.  
Ниша A: fail-closed gate тела Python-tool.

Три команды — единственный публичный контракт: `lock`, `judge`, `receipt`.

Ядро MIT. Платят потом за Action, реестр, подпись, инцидент — не в фазах C0–C3. Ценники в README не писать.

Ярусы (мысленно, не публиковать цены):

| Ярус | Что | Зачем |
|---|---|---|
| Open core (MIT) | `lock` / `judge` / `receipt`, CLI, supervisor, `locks/` в git | дистрибуция и аудит security-инструмента |
| Team | hosted registry, audit trail, уведомление о FAIL | первая платная единица из C5 |
| Enterprise | compliance-отчёт, инцидент, SLA | AI Governance из этого же файла |

Никогда в этом плане: SaaS-ОС, self-hosting, профили, markdown-спеки, `proven_pure`, каркас любого проекта, агрегатор как продукт, конкуренция с Pydantic, JS/WASM/второй язык, STOL, SKIPPED→PASS, двадцать адаптеров, ценники в README, MCP как второй harness до закрытой витрины CLI.

## 2. Нельзя сломать

- Хеш = декларация + канон тела (`ast.unparse`, иначе байткод). ArtifactRef не identity.
- `plan.lock` до run. Несовпадение → FAIL, тело не запускать.
- Нет исполнения → не PASS. Мало фактов → SKIPPED. `bool ≠ int`. pure+effects → FAIL.
- CLI `run --script` без `--plan` → SKIPPED. Worker не пишет PASS/FAIL.
- `judge_script` / Pipeline / Composite без пары plan+iface → SKIPPED. Self-lock не вердикт.
- Rust без worker → SKIPPED. Observation без worker не вердикт. С worker: identify → bind → run → verdict.

Стражи: `test_identity_hash`, `test_plan_lock_bind`, `test_purity_boundary`, `test_invariants`, `test_bones`, `test_committed_plan_matches_live_body`.

Канон хеша не «улучшать» без пересъёма всех `plan.json`.

## 3. Очередь

| Ф | Суть | Готово | Не делать |
|---|---|---|---|
| C0 | README + алиас `judge` | `4b87f13` копипаста зелёная | PyPI-ренейм, ценники |
| C1 | `receipt.json` | `judge --receipt`; без `proven_pure` | dashboard |
| C2 | GitHub Action + `locks/index.json` | workflow + index; подмена тела не PASS | hosted SaaS |
| C3 | 5 tools в `examples/tools/` | `.py`+`.json`+`.plan.json`; index bones+tools | сущность «новость» в ядре |
| C4 | один hook | PreToolUse bind; deny на чужой хеш; pre ≠ PASS | оба harness сразу |
| C5 | реестр замков в git | `locks --index`; сверка, не hosted | Governance $40k |
| C6 | подпись receipt | `receipt --verify`; Ed25519 локально | до стабильных C1–C2 |
| C7 | ниша B/C, API=CLI, один судья | API=CLI: без plan+iface не PASS | ниша B/C и слияние судей |

CLI `judge --plan` сверяет `runtime_hashes` (`c72ea42`). Второй hook (Cursor / Copilot / MCP) — не начинать, пока витрина CLI и один Claude hook зелёные. Готовые бинарники supervisor — GitHub Release, не `cargo` у покупателя; не в этом файле как фаза C.

Стартовать с C0. Не с Action, не с хука, не с подписи. Не начинать C(n+1), пока Cn не зелёная.

## 4. Старт

```bash
PYTHONPATH=. python -m pytest tests -q
PYTHONPATH=. python -m acid_engine lock --help
PYTHONPATH=. python -m acid_engine run --script examples/bones/n_plus_one.json --plan examples/bones/n_plus_one.plan.json --input '{"n": 3}'
```
