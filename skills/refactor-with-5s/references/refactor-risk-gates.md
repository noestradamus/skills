# Refactor Risk Gates

## Contents

- [Behavior contract](#behavior-contract)
- [Risk tiers](#risk-tiers)
- [Baseline and validation](#baseline-and-validation)
- [Deletion and consolidation gates](#deletion-and-consolidation-gates)
- [Protected artifacts](#protected-artifacts)
- [Discovered defects](#discovered-defects)
- [Version-control discipline](#version-control-discipline)

## Behavior contract

Refactoring preserves intended observable behavior unless a change is explicitly authorized. Check every relevant contract dimension:

- public API shape and compatibility;
- persisted data, schemas, migrations, and serialization;
- errors, status codes, exceptions, retries, and fallback behavior;
- authorization, authentication, privacy, and audit behavior;
- side effects, ordering, idempotency, transactions, and concurrency;
- numerical precision, randomness, units, and scientific reproducibility;
- timing, performance, memory, and resource use when users depend on them;
- logs, metrics, traces, alerts, and operational interfaces;
- CLI, configuration, environment variables, events, templates, and file formats.

Do not call an intentional contract change a refactor. Label and test it separately.

## Risk tiers

| Tier | Typical change | Minimum evidence |
| --- | --- | --- |
| **0 — Mechanical** | Remove unused imports, apply local formatting, rename an unexported symbol with tooling. | Static checks and targeted tests. |
| **1 — Local behavioral** | Extract or inline a function, simplify local control flow, remove verified private dead code. | Characterization or unit tests plus static checks. |
| **2 — Cross-boundary** | Move modules, consolidate implementations, narrow internal APIs, change dependency direction. | Call-path review, integration tests, broad static checks, and contract comparison. |
| **3 — Critical contract** | Public API, persistence, migration, auth, concurrency, distributed workflow, numerical core, billing, safety, or security-sensitive logic. | Explicit authorization, characterization, integration or end-to-end coverage, rollback awareness, and domain-specific validation. |

Escalate to the highest applicable tier. A small diff can still be Tier 3.

## Baseline and validation

Discover commands from repository configuration. Use the narrowest meaningful checks first, then broaden:

1. Relevant existing tests or characterization tests.
2. Formatter check for touched languages.
3. Linter and static analysis.
4. Type checker or compiler.
5. Integration or end-to-end tests around changed boundaries.
6. Build or package validation.
7. Benchmark, load, migration, security, numerical, or snapshot checks when contract-relevant.

Record command, result, and whether the result is pre-existing or introduced. When a full suite cannot run, state exactly what was not validated and why.

Use characterization tests when behavior is poorly documented. Capture current behavior before simplifying it; do not infer the intended result from the proposed refactor.

## Deletion and consolidation gates

Before deletion, answer all applicable questions:

- Is the candidate referenced statically?
- Can it be reached dynamically through strings, reflection, registration, dependency injection, plugins, routing, templates, or generated code?
- Is its name serialized, persisted, documented, exported, or consumed externally?
- Does configuration or CI invoke it?
- Does Git history show an intentional compatibility or operational reason?
- Is there a test or characterization proving removal preserves the contract?

Before consolidation, prove that implementations share:

- semantics and invariants;
- error and fallback behavior;
- performance and side-effect expectations;
- lifecycle and ownership;
- likely reasons to change.

If these differ, keep the implementations separate or extract only the genuinely shared primitive.

## Protected artifacts

Treat these as protected until explicitly included:

- generated source and generated documentation;
- database migrations and schema history;
- lockfiles and dependency resolution output;
- vendored or third-party code;
- snapshots and golden files;
- public headers, SDK surfaces, event schemas, and protocol definitions;
- localization identifiers and externally referenced resource names;
- security policy, authorization rules, audit paths, and secrets handling.

Modify the source generator rather than generated output. Update lockfiles only when dependency changes are in scope. Never rewrite migration history merely to make it look cleaner.

## Discovered defects

Refactoring often exposes bugs. Handle them visibly:

1. Reproduce the suspected defect.
2. Add a regression test when practical.
3. Determine whether fixing it is inside the authorized scope.
4. If authorized, separate the bug fix conceptually in the diff and report it as a behavior change.
5. If not authorized, preserve existing behavior and record the defect with evidence and impact.

Do not silently change behavior and then claim the refactor was behavior-preserving.

## Version-control discipline

- Inspect branch and status before editing.
- Preserve all unrelated user modifications.
- Keep refactor batches coherent and reviewable.
- Avoid mass renames mixed with semantic changes when they can be separated.
- Follow repository instructions for branching and commits.
- Do not commit unless requested or required by the user's established workflow.
- Never push, merge, rebase shared history, deploy, or publish without explicit instruction.
- Report final branch, commit state, and remaining modifications accurately.
