# Глоссарий

- **lock** — JSON замка на тело. Не вердикт.
- **judge** — bind до run + вердикт.
- **receipt** — Observation + PASS/FAIL/SKIPPED, без `proven_pure`.
- **plan.lock** — замороженные `module_hashes` и `interface_contract_hash`.
- **content_hash** — декларация + канон тела. `ArtifactRef` не входит.
- **Observation** — факты прогона. Observed ≠ Proven.
- **SKIPPED** — фактов мало, чтобы судить. Не PASS.
- **toolchain** — `python_version` + `canon_kind` + `worker_hash` + `runtime_hashes` рядом с замком, не в identity.
- **supervisor** — бинарь `acid-judge`: bind → worker → verdict. Не канон тела.
