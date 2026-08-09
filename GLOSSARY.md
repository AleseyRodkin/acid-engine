
```markdown
# Глоссарий

- **Contract** — универсальное описание сущности системы (идентификатор, характеристики, правила, действия).
- **Container** — иммутабельный снимок данных на порте.
- **ScriptModule** — минимальная исполняемая единица, содержащая спецификацию и реализацию.
- **CompositeModule** — модуль, состоящий из графа других модулей.
- **Pipeline** — замкнутый контур выполнения контракта (Container → Script → Module → Graph → Interface).
- **ConstraintResolver** — механизм слияния унаследованных и декларированных политик.
- **ContractRegistry** — реестр всех контрактов проекта с историей и разрешением ссылок.
- **ExecutionProfile** — способ упаковки проекта в артефакт (Library, CLI, Desktop, Service, SaaS, Embedded).
- **Observation** — наблюдаемые факты выполнения (latency, effects, trace).
- **Conformance** — проверка `Provided ⊨ Required`.
- **Self-hosting** — способность AcidEngine описывать и проверять собственные компоненты.
- **DSL** — человекочитаемый язык описания контрактов.
- **AIReferenceView** — представление кода для ИИ (атомарные ссылки на ScriptModule).