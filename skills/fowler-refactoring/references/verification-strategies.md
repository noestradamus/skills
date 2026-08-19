# Verification Strategies for Behavior-Preserving Refactoring

Build evidence that is proportionate to the change. Do not treat any single check as proof. Reuse the repository's own commands and compare post-change results with a recorded baseline.

## Table of contents

- [Discover repository-native checks](#discover-repository-native-checks)
- [Define observable invariants](#define-observable-invariants)
- [Record the baseline](#record-the-baseline)
- [Use an evidence ladder](#use-an-evidence-ladder)
- [Characterize legacy behavior](#characterize-legacy-behavior)
- [Verify common transformation risks](#verify-common-transformation-risks)
- [Handle performance-sensitive code](#handle-performance-sensitive-code)
- [Handle failing baselines](#handle-failing-baselines)
- [Review the final diff](#review-the-final-diff)
- [Report evidence and residual risk](#report-evidence-and-residual-risk)

## Discover repository-native checks

Inspect instructions, CI workflows, task runners, build manifests, and existing scripts before choosing commands. Prefer a documented wrapper or task over reconstructing its internals.

Use these files only as clues, not as permission to assume a command:

| Ecosystem clue | Inspect for repository-provided commands |
| --- | --- |
| Python: `pyproject.toml`, `tox.ini`, `noxfile.py`, `pytest.ini` | Project scripts, test targets, type-check and lint configuration, virtual-environment instructions |
| JavaScript or TypeScript: `package.json` plus a lockfile | Named scripts and the package manager selected by the existing lockfile |
| Java or JVM: `pom.xml`, `build.gradle*`, `gradlew`, `mvnw` | Wrapper tasks, modules, test filters, static analysis, integration profiles |
| C# or .NET: `.sln`, `.csproj`, `global.json` | Solution or project targets, test projects, analyzers, formatting checks |
| Go: `go.mod`, `Makefile`, task configuration | Package-scoped tests, vet or static analysis, generated-code rules |
| Rust: `Cargo.toml`, workspace configuration | Package or workspace checks, feature flags, clippy, formatting, benchmarks |
| Mixed repositories: CI and top-level task runners | The supported orchestration path and required service dependencies |

Do not install a missing dependency, switch package managers, create a new test framework, or update configuration merely to run a refactor unless the user authorizes it.

## Define observable invariants

Write only the invariants relevant to the target, but make them concrete. Consider:

- public function, method, class, CLI, event, and network interfaces;
- request and response shapes, schemas, serialized names, ordering, formatting, and compatibility;
- database reads and writes, transactions, migrations, identifiers, and persistence timing;
- returned values, mutations, I/O, logging, metrics, emitted events, notifications, and audit records;
- exception types, messages when contractual, error precedence, retry behavior, and exit codes;
- evaluation order, short-circuiting, laziness, callback order, cleanup, and resource lifetime;
- time, randomness, locale, floating-point behavior, numerical tolerance, and platform differences;
- asynchronous scheduling, cancellation, locking, atomicity, races, idempotency, and thread safety;
- authentication, authorization, tenant isolation, secrets handling, validation, and trust boundaries;
- latency, throughput, memory, allocation, or startup behavior only when measured or contractually important.

Treat internal implementation details as non-invariants unless another component can observe or depend on them.

## Record the baseline

1. Record the branch or revision and inspect version-control status.
2. List unrelated modified files and overlapping hunks that must remain untouched.
3. Record the exact focused commands selected from repository guidance.
4. Run the narrowest relevant behavioral test before broader static or build checks.
5. Capture exit status, failing test names, diagnostics, skipped tests, relevant environment constraints, and non-determinism.
6. Re-run a suspicious failure when needed to determine whether it is stable.
7. Save representative output or benchmark data only when it supports an identified invariant.

Use a compact baseline log:

```text
Command: <exact repository-provided command>
Scope: <module, package, test, or behavior>
Result: PASS | FAIL | BLOCKED
Pre-existing details: <failing cases or blocker>
Environment notes: <services, platform, feature flags, seed>
```

Do not edit first and reconstruct the baseline later.

## Use an evidence ladder

Choose the lightest set that can credibly catch the transformation's risks, then expand as the affected surface grows:

1. **Diff and syntax evidence:** Inspect the edit, parse or compile the changed unit, and run whitespace or formatter checks without broad reformatting.
2. **Focused behavior evidence:** Run the smallest unit, characterization, contract, or integration tests that exercise changed paths and invariants.
3. **Static interface evidence:** Run type checks, compiler checks, linters, analyzers, or dependency-boundary checks that the repository already uses.
4. **Affected-area evidence:** Run the relevant package, module, service, or workspace suite, including callers and implementations.
5. **System evidence:** Run the broadest practical repository suite, build, end-to-end check, or manual acceptance path when risk and cost justify it.
6. **Specialized evidence:** Add serialization fixtures, compatibility tests, concurrency tests, security checks, or benchmarks only when those dimensions are at risk.

Never claim that compilation alone proves behavior preservation. Likewise, do not claim that one focused test proves unaffected integration behavior.

## Characterize legacy behavior

Use characterization tests when existing tests do not protect the relevant behavior and current behavior can be captured safely.

1. Choose the narrowest stable seam: a public function, module boundary, service adapter, CLI invocation, or deterministic input-output path.
2. Assert externally visible results and side effects, not the current internal structure.
3. Include surprising edge cases that the refactor could accidentally “clean up.” Label them as current behavior rather than intended product requirements.
4. Control time, randomness, locale, network, filesystem, and external services only through patterns already accepted by the repository.
5. Avoid broad snapshots when a few explicit assertions express the contract more safely.
6. Keep golden files only when their format is stable, reviewable, and already conventional in the project.
7. Do not turn a suspected defect into a silent fix. Preserve it for the structural change and report it separately.
8. Stop when behavior cannot be observed without changing production semantics, exposing sensitive data, or inventing an unreliable harness.

Treat a characterization test as evidence of what the code does now, not automatic proof that the behavior is correct.

## Verify common transformation risks

### Extraction, inlining, and variable changes

- Assert argument and expression evaluation counts when calls can mutate, throw, block, or vary.
- Cover early returns, exceptions, cleanup, `await` or callback boundaries, and closure or receiver binding.
- Compare mutation, I/O, and event order before and after.

### Renaming and movement

- Use symbol-aware references plus text search for dynamic names.
- Inspect reflection, templates, configuration, dependency injection, serialization, routes, commands, ORM mappings, and generated clients.
- Test public imports and compatibility aliases when authorized.

### Duplication removal

- Prove the duplicated branches share semantics, not merely similar text.
- Build a case matrix for differing inputs, defaults, errors, side effects, and future change reasons.
- Keep separate implementations when an abstraction would require flags, optional fields, or branching that hides meaningful differences.

### Conditional simplification

- Write a truth table for interacting predicates.
- Preserve short-circuit order, side-effect counts, error precedence, logging, cleanup, and default cases.
- Test combinations, not only one case per branch.

### Query and mutation separation

- Check atomicity, transactions, locks, authorization, audit events, retries, and time-of-check/time-of-use races.
- Assert that mutation occurs exactly once and that callers cannot accidentally omit it.
- Avoid separation when one atomic operation is the behavior contract.

### Data and type refactoring

- Test null, empty, boundary, malformed, and legacy values.
- Verify equality, hashing, ordering, copying, identity, serialization, persistence, and language interop.
- Inspect schemas and wire formats directly; do not infer compatibility from type checking.

### Inheritance and delegation

- Run the same contract tests against every subtype or implementation.
- Cover clients typed through base interfaces and concrete types.
- Verify construction, override resolution, protected hooks, equality, serialization, dependency injection, and disposal.

### Security-sensitive code

- Preserve authorization order, tenant or user scoping, validation, redaction, audit logging, and failure behavior.
- Run existing negative-access and boundary tests, not only successful paths.
- Stop for explicit authorization when a trust boundary or policy would change.

### Concurrent or asynchronous code

- Preserve synchronization, ordering, cancellation, retries, idempotency, and resource ownership.
- Use existing deterministic concurrency tests or stress harnesses when available.
- Do not infer race safety from a passing sequential unit test.

## Handle performance-sensitive code

Treat optimization as a separate behavior or quality change unless the task merely restructures code and measured performance remains within the existing contract.

1. Identify the claimed bottleneck and the metric that matters.
2. Reuse an existing benchmark, profiler scenario, load test, or production-representative fixture.
3. Record workload, environment, warm-up, number of runs, variance, and baseline result.
4. Preserve correctness checks alongside performance measurements.
5. Refactor in small steps and remeasure after each meaningful change.
6. Reject a more complex design when improvement is absent, within noise, or irrelevant to the actual bottleneck.
7. Report environmental limits and avoid universal performance claims from one machine.

When no representative measurement is available, do not perform optimization-driven restructuring. Restrict the task to clarity changes that do not plausibly alter performance, or request authorization to establish a benchmark first.

## Handle failing baselines

- Re-run the identical command after the refactor and compare failing cases, diagnostics, and counts.
- Classify a failure as pre-existing only when baseline evidence supports that classification.
- Treat a changed failure mode, new failing case, timeout, or skipped check as a possible regression.
- Narrow the change or add focused evidence when a broad failing suite cannot distinguish outcomes.
- Do not repair unrelated baseline failures inside the refactor.
- Stop and report residual risk when the baseline is too unstable to support a credible comparison.

## Review the final diff

Inspect the complete diff, not only the last transformation. Check for:

- public signatures, serialized names, schemas, routes, commands, database mappings, or protocol changes;
- reordered predicates, side effects, I/O, events, exceptions, cleanup, transactions, or asynchronous operations;
- accidental bug fixes or changed edge-case handling;
- generated, vendored, migration, snapshot, lock, or third-party files;
- broad formatting, line-ending changes, import churn, or unrelated edits;
- duplicated compatibility paths, temporary shims, dead code, stale comments, and unused abstractions;
- new dependency cycles, wider public surface, hidden coupling, or complexity merely moved elsewhere;
- overlap with unrelated uncommitted work;
- tests that assert implementation details instead of behavior.

Run the repository's diff or whitespace check when available. Re-open the affected code as a reader and confirm that the original design problem is now easier to understand or change.

## Report evidence and residual risk

Use this structure:

```text
Scope and assumptions
- Target:
- Preserved invariants:
- Exclusions:

Problems and transformations
- Evidence:
- Technique and reason:
- Rollback boundary:

Verification
- Baseline commands and results:
- Post-change commands and results:
- Focused behavior evidence:
- Broader checks:

Status and risk
- Pre-existing failures:
- Remaining failures or blocked checks:
- Suspected bugs reported separately:
- Residual risk and assumptions:
- Recommended follow-up:
- Separately authorized behavior changes: none | <explicit list>
```

Distinguish code implementation, automated verification, manual acceptance, merge approval, deployment, and production approval. State only the level supported by evidence.
