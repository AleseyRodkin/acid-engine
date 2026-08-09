# Жизненный цикл контракта

1. **Declared** — контракт объявлен (Specification).
2. **Inherited** — унаследованы политики от родительских контрактов.
3. **Constraint Resolver** — вычисляется Effective (слияние Declared + Inherited + Defaults).
4. **Resolved** — создаётся неизменяемый plan.lock.
5. **Execution** — реализация выполняется, собираются Observation.
6. **Provided** — из Observation формируется Provided Contract.
7. **Conformance** — Provided сравнивается с Required.
8. **PASS / FAIL / SKIPPED** — результат проверки, при FAIL блокируется дальнейшее выполнение.