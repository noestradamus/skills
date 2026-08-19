# Verification Strategies

Choose evidence in proportion to the observable surface and risk. Reuse repository-provided tools and commands; do not assume a language, test framework, package manager, linter, or IDE.

## Contents

- [Build an invariant ledger](#build-an-invariant-ledger)
- [Discover and record the baseline](#discover-and-record-the-baseline)
- [Match checks to risks](#match-checks-to-risks)
- [Characterize legacy behavior](#characterize-legacy-behavior)
- [Verify performance and concurrency](#verify-performance-and-concurrency)
- [Compare and close out](#compare-and-close-out)

## Build an invariant ledger

Record only relevant surfaces, but inspect each category before excluding it:

| Surface | Examples | Useful evidence |
| --- | --- | --- |
| Return/output | Values, formatting, ordering, exit codes | Focused examples, reviewed golden output, property tests |
| Public contract | Exports, signatures, defaults, overloads, visibility | Caller tests, compile/type checks, API/schema diff tools |
| State and effects | Writes, events, network calls, logs, metrics | Fakes/spies, state snapshots, ordered-effect assertions |
| Errors | Type, contractual message, timing, retry behavior | Negative-path and fault-injection tests |
| Data boundary | Database schema, serialization, wire protocol | Round trips, fixtures, contract/compatibility tests |
| Identity/lifecycle | Aliasing, equality, construction, caching | Identity assertions, lifecycle and resource tests |
| Time/performance | Contractual latency, allocation, throughput | Existing representative benchmarks and profiles |
| Concurrency | Atomicity, locks, ordering, cancellation | Race detectors, stress/model tests, deterministic schedulers |
| Packaging/runtime | Imports, reflection, plugins, generated metadata | Build/package smoke tests and runtime discovery checks |

Preserve contract-relevant observables, not every incidental implementation artifact. Treat exact stack frames, symbol layout, logging text, or timing as invariants only when consumers, tests, operations, or the user rely on them. When unsure, ask rather than silently narrowing the contract.

## Discover and record the baseline

1. Read agent instructions, CI jobs, manifests, task runners, and nearby test documentation.
2. Identify the smallest command that exercises the target and the broad command normally used before merge.
3. Run available checks before adding characterization tests; those tests are the first codebase change.
4. Record command text, exit status, relevant output, working directory, and material environment details.
5. Classify failures as `relevant`, `demonstrably unrelated`, `flaky`, `environmental`, or `unclassified` and record supporting evidence.
6. Stop on relevant or unclassified baseline failures. Proceed past an unrelated, flaky, or environmental failure only when focused behavior evidence remains adequate, and disclose the limitation.
7. Avoid installing dependencies or altering configuration to obtain a baseline without authorization.

Use a compact ledger:

| Command | Scope | Baseline | Final | Interpretation |
| --- | --- | --- | --- | --- |
| repository command | target behavior | pass/fail/not run | pass/fail/not run | unchanged, improved, regressed, or inconclusive |

## Match checks to risks

- **Rename or move:** Use semantic references, search dynamic/config references, then run caller and build checks.
- **Extraction or inlining:** Test branch paths, effects, exceptions, binding, and evaluation count.
- **Conditional change:** Build a truth/path table and observe predicate and side-effect order.
- **Data or ownership move:** Test construction, mutation, identity, equality, persistence, and serialization.
- **API-adjacent change:** Diff signatures/schemas and run consumer or contract tests; keep compatibility unless change is authorized.
- **Hierarchy or dispatch change:** Run contract tests for every implementation and framework integration checks.
- **Dead-code removal:** Search non-code references and exercise packaging, reflection, flags, and plugin discovery.

Do not use a snapshot update as proof by itself. Inspect whether the new snapshot represents unchanged behavior. Do not accept a linter or compiler pass as a substitute for runtime behavior evidence.

## Characterize legacy behavior

When focused tests are absent:

1. Identify a narrow seam that can observe current inputs, outputs, state, effects, and errors.
2. Add examples for normal, boundary, and failure paths, including surprising behavior that callers may rely on.
3. Name assertions neutrally as current behavior; do not encode a desired bug fix.
4. Deliberately perturb a safe local copy or test double when practical to confirm the test can detect the relevant regression, then restore it.
5. Run the characterization test against otherwise unchanged production code and after every structural step.
6. Keep new test files within the authorized file scope; request confirmation before adding a harness elsewhere.
7. Stop if nondeterminism, unavailable systems, secrets, production-only data, or destructive effects prevent safe characterization.

Prefer a small characterization harness over a broad new test architecture. Do not change production visibility or public APIs solely to make a test convenient unless authorized.

## Verify performance and concurrency

Separate three cases. For optimization-driven work, require representative measurements before restructuring and compare before/after distributions rather than a single noisy run. For relied-upon latency, throughput, allocation, or timing, establish a benchmark or stop because preservation cannot be shown. For a maintainability refactor where performance is not contractual, behavior evidence may permit work to continue, but make no performance claim and report performance as unverified. Reuse existing benchmarks or profiles; otherwise propose a controlled measurement with the same workload, environment, warmup, and sample policy.

Treat concurrency changes as high risk. Preserve atomicity, synchronization boundaries, ordering, cancellation, retries, and resource lifetime. Use project-provided race, stress, model, or deterministic-scheduler checks. If a refactor must change these semantics, stop for explicit authorization.

## Compare and close out

1. Run the focused check after each meaningful transformation.
2. Run the broadest relevant practical suite at the final state.
3. Compare final results with the recorded baseline rather than reporting final status in isolation.
4. Compare the whole diff with the recorded pre-edit status/diff. Check for behavior edits, altered user hunks, unrelated churn, missed callers, stale comments, dead compatibility paths, generated changes, and formatting noise.
5. Map every invariant to evidence or label it `unverified` with the reason and residual risk.
6. If changes were staged or committed, verify that only task-owned files or hunks are included.
7. Report exact commands and outcomes. Use `not run` or `inconclusive` instead of implying success.

Use confidence language precisely:

- **Preserved with strong evidence:** Focused behavior checks and relevant broad checks match the baseline.
- **Preserved within tested scope:** Relevant focused checks match, but some broader surface was not exercised.
- **Not established:** Tests are missing, blocked, nondeterministic, or unrelated to the changed surface.
- **Behavior changed:** Treat the work as feature, fix, optimization, or restructuring; identify the change and confirm authorization.
