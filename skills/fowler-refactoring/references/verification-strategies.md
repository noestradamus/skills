# Verification Strategies for Behavior-Preserving Refactoring

## Contents

- [Detect repository-native verification](#detect-repository-native-verification)
- [Record the baseline](#record-the-baseline)
- [Build an invariant ledger](#build-an-invariant-ledger)
- [Use the verification ladder](#use-the-verification-ladder)
- [Add characterization tests safely](#add-characterization-tests-safely)
- [Verify control flow and side effects](#verify-control-flow-and-side-effects)
- [Verify public and compatibility boundaries](#verify-public-and-compatibility-boundaries)
- [Verify data and persistence boundaries](#verify-data-and-persistence-boundaries)
- [Verify security boundaries](#verify-security-boundaries)
- [Verify concurrency and asynchronous behavior](#verify-concurrency-and-asynchronous-behavior)
- [Verify performance-sensitive code](#verify-performance-sensitive-code)
- [Work safely with failing baselines](#work-safely-with-failing-baselines)
- [Protect unrelated working-tree changes](#protect-unrelated-working-tree-changes)
- [Review the final diff](#review-the-final-diff)
- [Stop when evidence is insufficient](#stop-when-evidence-is-insufficient)
- [Report verification evidence](#report-verification-evidence)

## Detect repository-native verification

Inspect the repository before inventing commands.

Look for applicable:

- repository and directory `AGENTS.md` files;
- contribution and development documentation;
- CI workflows and pipeline definitions;
- package manifests and task definitions;
- compiler, build-system, workspace, and solution files;
- test configuration and test directory conventions;
- formatter, linter, type-checker, static-analysis, coverage, and benchmark configuration;
- container, service, fixture, and environment setup;
- scripts used by maintainers for local or pre-commit checks.

Prefer commands already used by the repository. Run them from the documented working directory with the documented environment.

Do not assume:

- a package manager from the language alone;
- that all modules share one build;
- that a test filename implies a framework;
- that lint or compile proves runtime behavior;
- that a full suite is safe or affordable before focused checks;
- that missing dependencies may be installed or lockfiles changed without authorization.

When multiple commands exist, choose the smallest command that exercises the changed path, then expand.

## Record the baseline

Record the baseline before editing in a compact ledger:

| Field | Record |
| --- | --- |
| Target | Files, symbols, modules, runtime path, and explicit exclusions |
| Invariants | Observable behavior that must remain unchanged |
| Git state | Branch, status, unrelated modified paths, and relevant existing diff |
| Command | Exact command and working directory |
| Result | Pass, fail, skip, timeout, unavailable, or flaky |
| Evidence | Test counts, error summaries, warnings, artifacts, or benchmark statistics |
| Classification | Clean baseline, pre-existing failure, environmental blocker, or unknown |
| Coverage gap | Important behavior not exercised |
| Next proof | Characterization, focused test, contract check, manual smoke test, or user confirmation |

Preserve command output or a concise exact failure signature when it will be needed for comparison.

Re-run the same baseline command after the relevant change. Do not compare different commands and call them equivalent without explanation.

## Build an invariant ledger

Translate “do not change behavior” into testable statements.

Record applicable invariants for:

- returned, yielded, emitted, rendered, or serialized values;
- ordering, grouping, formatting, whitespace, locale, timezone, units, precision, and rounding;
- exceptions, error values, status codes, messages, and failure timing;
- mutation, persistence, logging, metrics, audit records, files, queues, and network calls;
- external call count, order, arguments, retry, timeout, and cancellation behavior;
- public names, signatures, defaults, overloads, exports, interfaces, and extension hooks;
- schema, field names, encodings, database representation, migrations, and compatibility;
- authorization, validation, sanitization, redaction, and trust boundaries;
- lock scope, atomicity, thread safety, task ordering, scheduling, and resource lifetime;
- deterministic versus randomized behavior;
- latency, throughput, memory, allocation, or other measured performance constraints.

Tie each planned transformation to the subset of invariants it could threaten.

## Use the verification ladder

Move from cheap and focused checks to broad and expensive checks.

### Level 1: Structural checks

Run applicable parsing, formatting checks, compilation, type checking, static analysis, import checks, dependency-boundary checks, or IDE diagnostics.

Use this level to catch syntax, resolution, visibility, signature, and type errors. Do not use it as proof of runtime equivalence.

### Level 2: Focused behavioral checks

Run the smallest existing tests that execute the changed path. Select tests by symbol, file, package, module, class, scenario, tag, or documented target.

Use this level after each meaningful transformation. Keep the feedback loop short enough to associate a failure with the latest step.

### Level 3: Neighboring and contract checks

Run the affected package, component, service, API contract, serializer, persistence adapter, integration, or consumer tests after a coherent group of steps.

Use this level when a refactor moves responsibilities, changes internal declarations, or crosses module boundaries.

### Level 4: Broad repository checks

Run the broadest practical relevant suite, build, packaging, generated-artifact comparison, or end-to-end smoke test before handoff.

State what was not run and why. Do not imply full validation when scope, environment, cost, or permissions prevented it.

### Level 5: Specialized checks

Add boundary-specific checks when applicable:

- API or ABI compatibility;
- schema and serialization round trips;
- migration or persistence compatibility;
- race detectors, schedulers, or concurrency stress tests;
- authorization and security regression tests;
- representative benchmarks or profilers;
- manual UI, CLI, service, or hardware smoke tests.

Use repository-provided specialized tooling before adding new infrastructure.

## Add characterization tests safely

Use characterization tests to capture current behavior when existing coverage is absent or insufficient.

1. Choose an externally meaningful seam close to the requested refactor.
2. Observe the current behavior with deterministic inputs and controlled dependencies.
3. Capture values, errors, state changes, external interactions, and ordering that the refactor could affect.
4. Include boundary, exceptional, and side-effect paths, not only the happy path.
5. Name the test after the behavior observed, not after an assumption that the behavior is correct.
6. Keep fixtures minimal and stable.
7. Avoid asserting private implementation details that the refactor intentionally needs to change.
8. Confirm that the test fails when the observed behavior is deliberately perturbed, when safe to do so.
9. Restore the original code and keep the characterization green before refactoring.
10. Report suspicious behavior as a possible bug rather than changing the expected value silently.

Do not add characterization tests that encode nondeterministic timestamps, random values, environment-specific paths, unstable ordering, or incidental logs without controlling them.

When no safe seam exists, reduce the refactor scope or request confirmation instead of manufacturing confidence.

## Verify control flow and side effects

Treat control-flow cleanup as high risk when predicates, branches, or helpers have effects.

Before changing a conditional:

1. List the meaningful input combinations as a truth table or decision table.
2. Mark which predicates run for each combination.
3. Record predicate order and short-circuit points.
4. Record branch-local mutations, external calls, errors, cleanup, and returns.
5. Identify work skipped by early exits.
6. Identify shared finalization, transactions, locks, or resource cleanup.

After changing it, verify:

- the same branch is selected for every meaningful combination;
- predicates execute in the same order and number when observable;
- skipped work remains skipped;
- external calls retain order, arguments, and retry behavior;
- return and exception paths remain equivalent;
- cleanup and finalization still run;
- no expression moved earlier into a path that previously avoided it.

Use spies, fakes, event logs, or deterministic test doubles only when consistent with repository practice.

## Verify public and compatibility boundaries

Treat a declaration as public when consumers can access it outside the edited implementation, even when the language does not mark it `public`.

Check:

- exported symbols and package entry points;
- interfaces, traits, protocols, abstract members, callbacks, and overrides;
- CLI commands, flags, environment variables, configuration keys, and file formats;
- HTTP, RPC, event, message, and plugin contracts;
- reflection, dependency injection, registration, framework conventions, and templates;
- source, binary, and behavioral compatibility for libraries;
- documented extension and test seams.

Do not change a public name, signature, default, error, or representation under the refactoring hat without explicit authorization.

When an internal refactor needs a transition:

1. Keep the old surface as a facade or adapter when authorized and proportionate.
2. Move callers incrementally.
3. Verify old and new paths.
4. Remove the compatibility layer only after usage evidence and authorization support removal.

Do not create an indefinite shim without recording its purpose and removal condition.

## Verify data and persistence boundaries

Before moving or wrapping data, capture:

- field and property names;
- type, nullability, defaults, units, and normalization;
- equality, hashing, ordering, and identity;
- serialization shape and versioning;
- database table, column, key, index, discriminator, and ORM mapping;
- migration and backward-reading requirements;
- copy versus reference semantics;
- mutation and ownership;
- precision, rounding, locale, and timezone.

Run applicable round-trip tests:

1. Read existing representation.
2. Construct or process the refactored internal form.
3. Write or serialize it.
4. Compare the external representation and behavior.
5. Verify old data remains readable.
6. Verify no migration or schema artifact changed unintentionally.

Stop for authorization when the transformation requires a schema, migration, or serialized-form change.

## Verify security boundaries

Treat authentication, authorization, validation, sanitization, redaction, secrets, and audit behavior as observable contracts.

Before editing, identify:

- the trust boundary and threat-relevant entry points;
- where identity and permissions are checked;
- validation order and canonicalization;
- fail-open versus fail-closed behavior;
- redaction and logging;
- audit events;
- transaction or race implications.

After editing, verify both allowed and denied paths. Confirm that checks still occur before protected side effects and that failures retain safe defaults.

Do not move a security check merely to improve code shape without proving equivalent ordering and coverage. Obtain explicit authorization for any policy change.

## Verify concurrency and asynchronous behavior

Assume extraction, movement, encapsulation, caching, and query separation can change concurrency semantics.

Record applicable:

- lock acquisition and release order;
- atomic regions and transactions;
- shared mutable state and memory visibility;
- task, goroutine, thread, actor, or event-loop ownership;
- await, yield, callback, and cancellation points;
- timeout and retry behavior;
- cleanup on cancellation or failure;
- ordering guarantees and idempotency.

Preserve the placement of synchronization and suspension points unless the user authorizes a semantic change.

Run repository-provided race detectors, stress tests, deterministic schedulers, or concurrency suites when available. Repeat flaky concurrency checks enough to characterize uncertainty, but do not claim a proof from one passing run.

Stop when a transformation creates a new race window or changes atomicity.

## Verify performance-sensitive code

Do not optimize from source appearance alone.

Before an optimization-driven transformation:

1. Define the performance question and user-relevant metric.
2. Select a representative workload and data distribution.
3. Record hardware, runtime, compiler, build mode, warm-up, concurrency, and environment.
4. Run enough iterations to estimate normal variance.
5. Use a profiler when the bottleneck location is uncertain.
6. Record baseline latency, throughput, memory, allocation, I/O, or resource use as relevant.

After the transformation:

1. Re-run the same measurement under comparable conditions.
2. Compare effect size with normal variance.
3. Run behavior checks independently.
4. Inspect whether the gain shifts cost to startup, memory, I/O, concurrency, or maintainability.
5. Retain the change only when evidence supports the trade-off.

When benchmarks do not exist and cannot be established safely, perform only readability-driven refactoring that does not claim performance improvement, or stop the performance portion.

## Work safely with failing baselines

When a baseline check fails:

1. Capture the exact command and failure signature.
2. Re-run when flakiness or environment issues are plausible.
3. Determine whether the failure touches the target path.
4. Prefer a narrower passing check that still exercises the target.
5. Add characterization only when it can isolate current behavior.
6. After editing, run the same failing command and compare signatures.
7. Treat new failures, changed failure locations, increased counts, or different outputs as possible regressions.
8. Report pre-existing failures separately from unverified risks.

Do not “fix” the baseline as unrelated cleanup. Do not weaken tests, suppress warnings, or change configuration to make the refactor appear green.

## Protect unrelated working-tree changes

Before editing:

- inspect branch, status, and relevant diffs;
- identify paths and hunks already modified;
- determine whether the target overlaps user work;
- preserve line endings, formatting scope, and generated state.

During editing:

- modify explicit files and bounded hunks;
- avoid repository-wide formatter or code-generation commands unless authorized;
- never run destructive reset, checkout, clean, or restore commands against user changes;
- do not stage unrelated files;
- re-open overlapping diffs after automated refactoring tools run.

After editing:

- compare status with the initial record;
- confirm unrelated files and hunks remain;
- explain unavoidable overlap;
- stop when safe separation cannot be established.

## Review the final diff

Review the complete diff independently of test results.

Check for:

- hidden behavior changes in renames, extractions, movements, or cleanup;
- changed evaluation order, repeated expressions, eager work, or lost short-circuiting;
- changed exception types, messages, wrapping, or timing;
- changed side-effect count, ordering, retries, logging, metrics, or audit;
- public exports, signatures, defaults, schemas, serialization, or configuration changes;
- changed locks, transactions, awaits, cancellation, or resource lifetime;
- dead code, unused imports, stale comments, aliases, adapters, and temporary scaffolding;
- architecture or abstraction larger than the diagnosed problem;
- unrelated formatting or file movement;
- generated, vendored, migration, snapshot, lock, or third-party changes;
- tests weakened, deleted, made less precise, or updated only to bless an accidental change;
- complexity moved rather than reduced.

Run `git diff --check` or an equivalent whitespace and conflict-marker check when available.

## Stop when evidence is insufficient

Stop or defer the affected transformation when:

- current behavior cannot be identified;
- tests cannot reach the path and safe characterization is unavailable;
- dynamic use of code proposed for removal cannot be excluded;
- a public, persistence, protocol, security, or concurrency boundary must change without authorization;
- a performance claim lacks representative measurement;
- unrelated user changes cannot be isolated;
- the baseline is too broken to distinguish regression;
- required services, data, hardware, credentials, or environment are unavailable;
- the proposed abstraction has no concrete present need;
- the latest step cannot be rolled back or verified independently.

Preserve the last verified state. State the exact missing evidence, affected invariant, residual risk, and safest next action.

## Report verification evidence

Use a compact evidence table:

| Stage | Command or check | Result | Compared with baseline | Scope or limitation |
| --- | --- | --- | --- | --- |
| Baseline | Exact command | Pass/fail | Initial | Target behavior covered |
| Increment | Focused command | Pass/fail | Same or new focused check | Transformation protected |
| Broad | Suite/build/contract check | Pass/fail/not run | Baseline comparison | Repository boundary covered |
| Specialized | Compatibility/race/security/benchmark/manual | Result | Before/after when applicable | Environment and limitations |
| Diff review | `git diff --check` and manual review | Pass/issues | Initial status comparison | Unrelated changes preserved |

Conclude with separate statements for:

- implementation status;
- automated verification status;
- manual verification status;
- pre-existing failures;
- unverified boundaries;
- suspected bugs not fixed;
- behavior changes requiring authorization;
- merge, deployment, and production status.
