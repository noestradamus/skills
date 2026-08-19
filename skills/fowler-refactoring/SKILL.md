---
name: fowler-refactoring
description: Refactor existing code safely through small, behavior-preserving transformations grounded in Martin Fowler's refactoring principles. Use when an autonomous coding agent must improve names, structure, responsibilities, duplication, conditionals, data flow, coupling, or extensibility in a real repository without changing observable behavior, including requests that mix cleanup with a bug fix or new feature. Do not use for greenfield design, feature-first rewrites, dependency upgrades, migrations, or optimization without a measured baseline.
---

# Fowler Refactoring

## Purpose

Improve the internal design of existing code without changing its externally observable behavior. Apply a sequence of small, reversible transformations; verify after meaningful steps; and stop at boundaries that require authorization.

Read [references/fowler-principles.md](references/fowler-principles.md) before classifying the work. Read only the relevant entries in [references/refactoring-catalog.md](references/refactoring-catalog.md) when selecting transformations. Read [references/verification-strategies.md](references/verification-strategies.md) before baselining legacy code, touching high-risk logic, or performing final verification.

## Operating contract

- Apply Fowler's two-hats discipline: wear the refactoring hat or the behavior-change hat, never both in the same step. Keep behavior-preserving refactoring separate from feature additions, bug fixes, dependency upgrades, migrations, and optimizations.
- Preserve observable contracts unless the user explicitly authorizes a separate behavior change. Include public APIs, schemas, serialized forms, persistence, protocols, side effects, exception behavior, ordering, timing-sensitive behavior, concurrency, security boundaries, and compatibility when relevant.
- Treat code smells as prompts to investigate, not commands to change code.
- Choose the smallest coherent refactoring that addresses demonstrated design friction. Reject speculative abstractions and cleanup without a concrete payoff.
- Work in small rollback units. Keep the repository runnable and re-run focused checks frequently.
- Reuse repository-provided commands, language idioms, and architectural conventions. Do not impose a universal framework or folder structure.
- Preserve unrelated work. Never reset, overwrite, reformat, stage, or commit changes outside the agreed scope.
- Avoid generated, vendored, migration, snapshot, lock, and third-party files unless the user explicitly includes them. Change a generator rather than generated output when possible.
- Do not install dependencies, alter configuration, update lockfiles, push, merge, deploy, or publish unless necessary and authorized.
- Measure representative performance before restructuring for speed. Do not call an unmeasured cleanup an optimization.

## Workflow

### 1. Establish scope

1. Read repository-level and directory-level instructions, including agent guidance, contribution rules, build files, CI workflows, and package-specific conventions.
2. Restate the requested outcome, permitted files, explicit exclusions, and whether the task is refactoring-only or mixed with behavior work.
3. Inspect version-control status and the relevant diff. Record unrelated existing modifications and keep them untouched; do not reset, overwrite, reformat, stage, or commit them.
4. Trace the target's entry points, callers, implementations, tests, data flow, side effects, runtime registration, and external boundaries.
5. Define the behavior-preservation contract for this task. Name concrete invariants rather than saying only “behavior stays the same.”
6. Bound vague requests such as “clean up this module” to the smallest bounded problem supported by concrete evidence in the requested area. State the chosen scope and non-goals before broad edits.
7. Ask one concise clarification question only when a missing answer could materially change behavior, public compatibility, or permitted scope. Otherwise proceed with explicit assumptions.

### 2. Establish a baseline

1. Discover verification commands from repository configuration, CI, documentation, and existing scripts. Do not guess a package manager or test framework.
2. Run the narrowest relevant tests first, followed by applicable type checks, linters, builds, static analysis, or benchmarks already supplied by the project.
3. Record each command, result, environment-sensitive limitation, and pre-existing failure before editing.
4. Re-run an ambiguous failure when needed to determine whether it is stable and predates the refactor.
5. When useful tests are missing, add the smallest focused characterization tests that capture current externally visible outcomes and side effects. Do not “correct” surprising behavior inside those tests.
6. Treat compilation or type checking as supporting evidence, never as sole proof of behavior preservation.

Use [references/verification-strategies.md](references/verification-strategies.md) to select a proportionate evidence set.

### 3. Diagnose before changing

1. Identify concrete maintainability problems and cite exact files, symbols, call paths, or repeated logic.
2. Explain the local cost of each problem: difficult reasoning, duplicated change effort, unclear ownership, coupling, unsafe extension, or hidden side effects.
3. Distinguish structural problems from personal style preferences and repository-consistent patterns.
4. Map each supported problem to the smallest suitable technique in [references/refactoring-catalog.md](references/refactoring-catalog.md).
5. Consolidate duplication only after proving the cases have the same semantics and compatible change reasons. Defer candidates whose benefit, semantics, usage, or safety cannot be established.
6. Avoid broad formatting, mass renaming, folder movement, or architectural rewriting unrelated to the requested outcome.

### 4. Plan small transformations

Create an ordered plan of independently understandable steps. For every step, record:

- **Problem and evidence** — what design friction the step addresses.
- **Transformation** — the exact structural change.
- **Invariant** — what must remain observably unchanged.
- **Verification** — the focused check that can catch a mistake.
- **Risk and rollback** — `low`, `medium`, or `high`, plus the edit or commit boundary to revert.

Classify local private renames and simple extractions as low risk only when all references and effects are known. Classify cross-module movement, duplication removal, and side-effectful conditional changes as at least medium risk. Classify published APIs, schemas, protocols, persistence, authentication or authorization, concurrency, reflection, binary compatibility, and performance-sensitive paths as high risk.

Present the plan before editing when the work is large, cross-cutting, high risk, or requires a protected boundary. For a small, clearly authorized refactor, proceed directly while keeping the same step record internally.

### 5. Refactor incrementally

1. Apply one coherent transformation at a time.
2. Keep structural edits separate from behavior edits. Finish and verify the refactoring hat before starting any separately authorized feature or bug-fix hat.
3. Preserve evaluation order, short-circuiting, mutation count, I/O, resource lifetime, exceptions, asynchronous behavior, and cleanup semantics unless proved irrelevant.
4. Re-run the narrowest useful verification after each meaningful step. Expand verification as the affected surface grows.
5. Preserve existing style and architecture unless changing that convention is the explicit goal.
6. Prefer native language and framework idioms. Use automated refactoring tools when available, but inspect their complete diff and verify the result.
7. Avoid compatibility shims, new abstractions, or generic utility layers unless current evidence justifies them.
8. Do not hide behavior changes inside renames, extraction, movement, deduplication, or “cleanup.”
9. Keep churn proportional. Do not reformat untouched code or modify protected artifacts incidentally.

### 6. Handle discoveries safely

Stop, separate, or escalate under these rules:

- **Suspected bug:** Preserve the current behavior during the refactor. Do not silently fix it. Report the defect separately with evidence; fix it only under a separately authorized behavior-change hat.
- **Unclear current behavior:** Add a focused characterization test when safe. Otherwise ask for the missing contract or stop with the unresolved risk.
- **Protected boundary:** Obtain explicit authorization before changing a published API, persistence schema, serialization format, protocol, security boundary, concurrency semantics, or externally visible behavior.
- **Failing baseline:** Compare the same command before and after. Do not attribute a pre-existing failure to the refactor or use it to excuse a new regression.
- **Impossible verification:** Stop expanding the change. Explain what could not be verified, what evidence exists, and what residual risk remains.
- **Unnecessary abstraction:** Challenge the requested design with concrete complexity, coupling, or maintenance costs. Prefer the smaller change.
- **Unmeasured performance path:** Measure before optimization. Preserve the current structure or first establish a representative benchmark; do not optimize by intuition alone.
- **Overlapping unrelated edits:** Avoid the overlap or isolate only the intended hunks. Do not discard or rewrite another person's work.

### 7. Verify and report

1. Run focused tests for the changed behavior, then the broadest relevant verification practical for the repository.
2. Compare every result with the recorded baseline and separate regressions from pre-existing failures.
3. Review the full diff for accidental behavior changes, unrelated edits, dead code, stale comments, duplicate compatibility paths, protected artifacts, and excessive churn.
4. Confirm that the refactor removed or clarified the identified design problem rather than moving it behind a less visible abstraction.
5. Report:
   - scope, assumptions, and preserved invariants;
   - concrete design problems addressed;
   - transformations performed and why they were chosen;
   - behavior-preservation evidence;
   - exact tests and checks run with results;
   - pre-existing and remaining failures;
   - risks, deferred candidates, and recommended follow-up work;
   - any separately authorized behavior changes, clearly labeled as non-refactoring work.
6. Distinguish implementation completion from automated verification, manual acceptance, merge approval, deployment, and production approval.
7. Avoid claiming absolute proof. State the evidence and residual uncertainty proportionately.

## Completion gate

Declare the refactor complete only when all applicable conditions hold:

- Keep the agreed observable contract unchanged, or separate every explicitly authorized behavior change.
- Introduce no new failure relative to the recorded baseline.
- Address each changed area with concrete design evidence rather than taste alone.
- Keep each transformation reviewable and reversible.
- Preserve unrelated modifications and protected artifacts.
- Leave names, responsibilities, abstractions, data flow, or dependency boundaries clearer than before.
- Run and report the strongest practical verification for the affected surface.
- Record unresolved risks instead of concealing them.
