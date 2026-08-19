---
name: fowler-refactoring
description: Guide an autonomous coding agent through small, behavior-preserving refactorings grounded primarily in Martin Fowler's principles. Use when asked to refactor, clean up, simplify, rename, extract, move, de-duplicate, reduce coupling, untangle conditionals, reorganize responsibilities, or improve maintainability in an existing codebase without changing observable behavior. Also use to separate structural cleanup from feature or bug work. Do not use as authority for broad rewrites or unauthorized API, schema, protocol, security, concurrency, or performance changes.
---

# Fowler Refactoring

## Purpose

Improve the internal design of existing code without unintentionally changing what callers, users, operators, persisted data, or integrated systems can observe.

Apply a disciplined sequence of small transformations. Keep the code working, verify frequently, and stop when behavior preservation cannot be demonstrated.

Read [references/fowler-principles.md](references/fowler-principles.md) before diagnosing the target. Consult only the relevant entries in [references/refactoring-catalog.md](references/refactoring-catalog.md) when choosing a technique. Use [references/verification-strategies.md](references/verification-strategies.md) to establish the baseline, design characterization tests, and select checks.

## Operating contract

- Preserve observable behavior unless the user explicitly authorizes a separate behavior change.
- Wear one hat at a time: either refactor or add/change behavior. Never hide one inside the other.
- Apply the smallest coherent transformation that addresses the demonstrated design problem.
- Treat code smells as prompts to investigate, not commands to modify code.
- Keep transformations small, understandable, reversible, and independently verifiable.
- Re-run focused checks after meaningful steps instead of waiting for one final test run.
- Preserve public APIs, schemas, serialization, protocols, side effects, exceptions, ordering, security decisions, concurrency semantics, and timing-sensitive behavior unless explicitly authorized.
- Measure before restructuring for performance. Do not claim an optimization without representative before-and-after evidence.
- Avoid speculative abstractions, premature generalization, architecture replacement, broad formatting, and unrelated cleanup.
- Preserve repository conventions, generated boundaries, and unrelated user modifications.
- Leave the touched code easier to understand and cheaper to change than before.

Treat behavior preservation, small steps, frequent verification, code smells as diagnostic signals, the two-hats distinction, and the named catalog transformations as Fowler-derived foundations. Treat repository-state protection, contract inventories, characterization-test guidance, high-risk escalation, and final diff controls as additional safeguards supplied by this skill. See [references/fowler-principles.md](references/fowler-principles.md).

## Workflow

### 1. Establish scope

1. Read repository-level and directory-level instructions before editing, including applicable `AGENTS.md`, contribution guidance, build files, CI configuration, architecture notes, and package documentation.
2. Restate the requested outcome, target files or modules, constraints, permitted files, and explicit non-goals.
3. Inspect version-control status and relevant diffs. Record unrelated modifications and leave them untouched. Never reset, discard, overwrite, or broadly reformat user work.
4. Trace the relevant entry points, callers, callees, tests, exports, data flow, side effects, configuration, persistence, and runtime boundaries.
5. Define the observable invariants that must remain unchanged. Include applicable values, ordering, formatting, exceptions, side effects, external calls, persisted forms, authorization decisions, concurrency, and performance-sensitive behavior.
6. Classify a mixed request into separate refactoring and behavior-change phases. Keep the refactoring phase behavior-preserving.
7. Ask a concise clarification question only when unresolved ambiguity could materially change behavior, compatibility, or scope. Otherwise choose the narrowest safe interpretation and state it.

For a vague request such as “clean up this module,” first bound the work to concrete evidence in the named area. Do not infer permission for repository-wide cleanup.

### 2. Establish a baseline

1. Discover the project's existing commands from repository files and CI. Do not assume a language, package manager, test framework, linter, formatter, or IDE.
2. Run the narrowest relevant existing tests, type checks, linters, builds, static analysis, or smoke checks before editing.
3. Record each command and result. Separate pre-existing failures, warnings, and flaky behavior from later regressions.
4. Do not install dependencies, change configuration, update generated files, or modify lockfiles merely to create a cleaner baseline. Do so only when necessary and authorized.
5. When tests are missing or weak, add focused characterization tests only when they can capture current observable behavior without inventing new requirements.
6. Never treat successful compilation, type checking, linting, or formatting alone as proof of behavior preservation.

If the baseline cannot exercise the intended path, reduce scope, add safe characterization, request clarification, or report the residual risk before editing.

### 3. Diagnose before changing

For every candidate issue, record:

- **Evidence:** Point to concrete code, call paths, duplication, dependencies, or change friction.
- **Impact:** Explain why the issue makes this code harder to understand or modify.
- **Technique:** Select the smallest suitable transformation or local design adjustment.
- **Invariant:** State what behavior must remain unchanged.
- **Non-goal:** Exclude adjacent style preferences, bugs, features, and architecture changes.

Distinguish genuine design problems from subjective preferences. Do not rename, reformat, move, or abstract broadly without evidence tied to the requested outcome.

Challenge a requested abstraction when it would add more indirection, coupling, concepts, or extension machinery than the demonstrated problem warrants.

### 4. Plan small transformations

Create an ordered sequence of independently understandable steps. For each step, state:

- the problem being addressed;
- the intended transformation;
- the behavior that must remain invariant;
- the focused verification to run;
- the risk level;
- the rollback boundary.

Use these risk levels:

- **Low:** Keep the change private and local, with strong focused coverage and no meaningful side effects.
- **Medium:** Cross an internal module boundary, move state or side effects, or rely on partial coverage.
- **High:** Touch a public contract, persistence, serialization, protocol, security boundary, concurrency, numerical semantics, performance-critical path, or poorly understood legacy behavior.

Present the plan before editing when the work is medium or high risk, spans multiple responsibilities or modules, or requires several dependent transformations. Proceed directly only for a small, clearly authorized, low-risk refactor.

### 5. Refactor incrementally

1. Apply one coherent transformation at a time.
2. Keep structural changes separate from feature additions, bug fixes, dependency upgrades, and configuration changes.
3. Preserve evaluation order, call count, mutation timing, short-circuit behavior, cleanup, async behavior, exception behavior, and resource lifetime.
4. Use language or IDE refactoring support when reliable, but inspect its diff and verify the result.
5. Follow local naming, formatting, module, error-handling, and architectural conventions unless those conventions are the explicit target.
6. Prefer native language and framework idioms over a universal architecture.
7. Avoid editing generated, vendored, migration, snapshot, lock, or third-party code unless the user explicitly includes it. Change the source generator when appropriate.
8. Re-run the focused verification after each meaningful step. Revert or repair the latest small step immediately when it breaks the invariant.
9. Remove temporary compatibility scaffolding only after all callers have moved and verification proves it is unnecessary.
10. Keep comments aligned with intent. Remove stale explanations created obsolete by clearer code; retain comments that explain non-obvious constraints.

Do not hide a behavior change inside extraction, movement, renaming, conditional cleanup, dead-code removal, or abstraction.

### 6. Handle discoveries safely

- **Suspected bug:** Report it separately with evidence. Do not silently fix it under the refactoring hat.
- **Unclear behavior:** Capture the current behavior with characterization tests when safe; otherwise ask or stop.
- **Protected boundary:** Obtain explicit authorization before changing a public API, schema, serialized form, protocol, security rule, concurrency contract, or externally visible behavior.
- **Failing baseline:** Re-run the same command and determine whether the failure predates the refactor. Do not relabel an existing failure as a regression or dismiss a new failure as pre-existing.
- **Impossible verification:** Stop the affected transformation, preserve the last verified state, and explain the unverified risk.
- **Performance concern without evidence:** Establish a representative benchmark or profiler result before optimization-driven restructuring.
- **Over-general design:** Prefer duplication or a smaller local refactor when the proposed abstraction would erase meaningful differences or anticipate unsupported future needs.
- **Overlapping user changes:** Isolate edits by file or hunk. Stop when safe separation is not possible.

### 7. Verify and review

1. Re-run the focused checks used during the refactor.
2. Run the broadest relevant verification practical for the repository: tests, type checks, lint, build, integration checks, contract checks, race detection, benchmarks, or manual smoke tests as applicable.
3. Compare every result with the recorded baseline.
4. Review the final diff for:
   - accidental behavior or contract changes;
   - unrelated edits or formatting churn;
   - changed evaluation order, call count, side effects, or exception paths;
   - dead code, stale aliases, obsolete comments, and temporary scaffolding;
   - unnecessary indirection or abstractions larger than the original problem;
   - edits to generated, vendored, migration, snapshot, configuration, or lock files;
   - weakened tests or assertions that merely accommodate the refactor.
5. Run `git diff --check` or the repository-equivalent whitespace check when available.
6. Confirm that complexity was removed rather than moved behind a harder-to-follow boundary.

Do not declare behavior preservation from a passing narrow test when broader relevant boundaries remain unverified.

### 8. Report

Summarize:

- **Scope and invariants**
- **Design problems addressed**, with concrete evidence
- **Refactorings performed**, in execution order
- **Behavior-preservation evidence**
- **Baseline and final commands**, with results
- **Pre-existing and remaining failures**
- **Unchanged public and runtime boundaries**
- **Risks and assumptions**
- **Deferred bugs, behavior changes, or follow-up work**

Distinguish implementation completion from automated verification, manual acceptance, merge approval, deployment approval, and production validation.

## Completion gate

Declare the refactor complete only when:

- every change is behavior-preserving or separately authorized and labeled;
- no relevant check regressed from the baseline without an accepted explanation;
- protected contracts remain unchanged;
- unrelated modifications remain intact;
- the final diff is bounded and reviewable;
- the identified design problem is materially reduced;
- the result is easier to understand and change;
- all residual uncertainty is explicit.
