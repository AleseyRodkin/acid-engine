# Contract lifecycle

1. **Declared** — the contract is declared (Specification).
2. **Inherited** — policies inherited from parent contracts.
3. **Constraint Resolver** — Effective is computed (Declared + Inherited + Defaults).
4. **Resolved** — an immutable plan.lock is created.
5. **Execution** — the implementation runs; Observation is collected.
6. **Provided** — a Provided Contract is built from Observation.
7. **Conformance** — Provided is compared with Required.
8. **PASS / FAIL / SKIPPED** — the check result; FAIL blocks further execution.
