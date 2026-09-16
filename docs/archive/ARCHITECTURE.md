# AcidEngine architecture

> **Archive.** Not a plan and not the law. The “development OS” tail before the 21.08.2026 narrowing.
> Law: [METHOD.md](../../METHOD.md). Queue: [PLAN.md](PLAN.md).
> The live face of the repository is [README.md](../../README.md): lock → bind → observe.

AcidEngine was described as a contract-oriented development operating system.
Every element of the system is described by one mechanism — a **contract**.
The project has a strict level hierarchy, where each next level is implemented by means of the previous one.

## Levels

### Level 0 — Code views
- **LiveCodeView** — live executable code (ordinary Python functions or any other language).
- **AIReferenceView** — a reference view for AI (each atom is a separate `ScriptModule`; the AI edits only the atom).
- **HumanReadableView** — human-readable display of contracts (Specification / Input / Output / Implementation) and the dependency graph.

### Level 1 — Data store
- **DataPlane** — abstract store interface (`store`, `load`, `exists`).
- Temporary implementation: `InMemoryDataPlane`. A Rust implementation was planned.

### Level 2 — Contract layer
- **Contract** — base contract class (entity, attributes, rules, actions).
- **Specification**, **Policy**, **Parameters**, **ImplementationRequirements**.
- **ConstraintResolver** with strategies (min/max, intersection/union, boolean strengthen, string enum).
- **Semantic predicates** (equals, contains, matches, cardinality, json_schema, jsonpath, invariant, security).
- **InterfaceContract** — the contract of the whole application.

### Level 3 — Closed loop
- **Pipeline** — explicit class encapsulating Container → Script → Module → Graph → Interface → main().
- **ScriptModule**, **AsyncScriptModule**, **ContainerSnapshot**, **PortRef**, **DependencyGraph**.
- **ExecutionProfile** — universal interfaces for packing a project into artifacts:
  - `LibraryProfile`
  - `CLIProfile`
  - `DesktopProfile`
  - `ServiceProfile`
  - `SaaSProfile`
  - `EmbeddedProfile`

### Level 4 — Atom library
- **ContractRegistry** — a registry of all contracts with version history, reference resolution, and hash lookup.

## Services (developed in parallel)
- **Logging** (`ExecutionLogger`)
- **AI context** (`AIContextProvider`) — building context for an LLM.
- **DSL** — a parser of a human-readable contract language.
- **Security** — a `security` predicate for launching external vulnerability scanners.

## Self-application
AcidEngine itself was a project that assembled itself through its own contracts and profiles, then packed the resulting library into CLI, Desktop, and other forms. Any new mechanism had to work both for user projects and for the platform itself.

## Nested stubs
Each level receives a reference to the one below and by default delegates calls to it. When adding new behaviour only the needed method is overridden; the rest is picked up automatically.
