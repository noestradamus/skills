---
name: fowler-refactoring
description: Refactor existing code in small, behavior-preserving steps when a user asks to clean up, restructure, simplify, or improve maintainability; also separate the refactoring phase when a request mixes cleanup with a feature or fix.
---

# Fowler Refactoring

Improve internal design without changing externally observable behavior. Use Fowler's refactoring principles as the conceptual foundation and apply the repository safeguards below to autonomous work.

## Keep the boundary explicit

- Define contract-relevant observable behavior before editing. Include public APIs, schemas, serialized forms, outputs, side effects and their order, exceptions, compatibility, and any relied-upon timing or concurrency semantics.
- Wear one hat at a time. Separate structural refactoring from feature additions, bug fixes, optimizations, dependency upgrades, migrations, and other behavior changes.
- Partition a mixed request into independently verified phases. Keep the refactoring phase behavior-preserving even when the user also authorizes a later behavior change.
- Treat a suspected bug as current behavior until the user authorizes a fix. Report it separately; never conceal a fix inside cleanup.
- Prefer the smallest transformation that resolves the evidenced design problem. Reject speculative abstraction and unnecessary generality.

Read [Fowler principles and attribution](references/fowler-principles.md) before attributing guidance to Fowler or deciding whether a smell justifies work. Read the relevant entries in the [operational catalog](references/refactoring-catalog.md) when selecting or applying a transformation. Read [verification strategies](references/verification-strategies.md) when defining invariants, working without tests, or handling API, stateful, concurrent, timing-sensitive, or performance-sensitive code.

## 1. Establish scope

1. Read repository-level and applicable directory-level agent instructions.
2. Restate the requested outcome, permitted files, exclusions, and authorization boundary.
3. Inspect and record repository status plus relevant target diffs before editing. Treat unrelated modifications as user-owned; do not overwrite, reformat, stage, revert, stash, reset, or check them out to manufacture a clean baseline.
4. Trace the target's callers, callees, tests, data contracts, public interfaces, and runtime boundaries. Identify generated, vendored, migration, snapshot, and third-party files and exclude them unless explicitly requested.
5. Record the observable invariants that must remain unchanged and the evidence available for each.
6. Ask a concise question only when unresolved ambiguity could materially change behavior or scope. Otherwise make the narrowest safe assumption and state it.

Classify risk before planning:

- **Low:** local private rename, extraction, or simplification with focused tests.
- **Medium:** cross-file movement, shared data flow, duplicated logic, or indirect side effects.
- **High:** public API, persistence, serialization, protocol, security, concurrency, performance, contractual timing, or poorly understood legacy behavior.

Present a bounded plan before editing a vague cleanup request or medium-, high-, or large-scope work. Proceed directly only for small, specifically targeted, clearly authorized work.

## 2. Establish a baseline

1. Discover project-provided commands from local instructions, manifests, task runners, CI configuration, and nearby documentation. Reuse them instead of inventing a toolchain.
2. Run the narrowest relevant tests first, then the relevant type checks, linters, builds, or static analysis practical before editing.
3. Record each command, result, and relevant environment detail. Classify pre-existing failures as relevant, demonstrably unrelated, flaky, environmental, or unclassified.
4. Do not install dependencies, change configuration, or update lockfiles unless necessary and authorized.
5. Stop on relevant or unclassified baseline failures. Proceed past a demonstrably unrelated, flaky, or environmental failure only when focused evidence remains adequate, and disclose the limitation.
6. If coverage is missing, add focused characterization tests only when they can capture current behavior without asserting a desired fix. Run available checks first, then add the characterization test as the first codebase change against otherwise unchanged production code. Keep the test within the permitted file scope or obtain confirmation before expanding it. If behavior cannot be established safely, stop and explain the risk.
7. Do not treat compilation, type checking, snapshots alone, or a green unrelated suite as proof of behavior preservation.

## 3. Diagnose before changing

For every proposed change, identify:

- the concrete code evidence;
- the maintenance or changeability cost in this repository;
- the smallest suitable transformation;
- the behavior and boundary that could be disturbed.

Treat smells as prompts to investigate, not automatic defects. Distinguish design friction from personal style. Avoid broad formatting, global renaming, dependency churn, or architectural rewrites that do not serve the stated goal. Challenge a requested abstraction when its added indirection exceeds the demonstrated need.

Before consolidating duplication, prove that the fragments represent the same domain concept and share a reason to change; superficial similarity alone does not justify a shared abstraction.

## 4. Plan small transformations

Order coherent, reversible steps. For each step, state:

| Field | Required content |
| --- | --- |
| Problem | Specific evidence and why it impedes the requested change or understanding |
| Transformation | One named refactoring or narrowly described design adjustment |
| Invariant | Observable behavior that must remain unchanged |
| Verification | Focused check that can detect a mistake in this step |
| Risk and rollback | Low, medium, or high; files affected; last known-good boundary |

Prefer steps that leave the code runnable and reviewable. Split a step again when its diff cannot be explained as one structural transformation.

## 5. Refactor incrementally

1. Apply one coherent transformation at a time.
2. Preserve local style, architecture, language idioms, and framework conventions unless they are the explicit target.
3. Keep compatibility shims when an authorized internal move would otherwise disturb callers; remove them only with explicit API authorization.
4. Run the focused verification after each meaningful step. If it fails, inspect or roll back only that step before continuing.
5. Keep structural edits separate from behavior edits in the diff and, when practical, in commits.
6. Avoid incidental formatting and file churn. Do not regenerate snapshots or generated artifacts merely to make failures disappear.
7. Reassess scope when a transformation reveals wider coupling. Do not let discovery silently expand the task.
8. If a commit or publication is separately authorized, stage only task-owned files or hunks and recheck that pre-existing work is excluded.

## 6. Stop or escalate safely

| Discovery | Required response |
| --- | --- |
| Apparent bug | Preserve it, record evidence, and request separate authorization to fix it. |
| Potential security, privacy, corruption, or data-loss defect | Stop immediately, preserve non-sensitive evidence, and alert the user; do not hide it inside the refactor. |
| Unclear current behavior | Characterize it with a focused test or ask the user before editing. |
| Public API, schema, protocol, security, concurrency, or visible behavior must change | Stop that path and obtain explicit authorization. |
| Baseline check fails | Determine and record whether it predates the refactor; do not claim a fully green baseline. |
| Verification becomes unavailable or inconclusive | Stop at the last verified boundary and explain residual risk. |
| Optimization motivates restructuring without representative measurements | Measure first or decline the optimization-driven refactor. |
| Relied-upon performance lacks representative measurements | Establish a benchmark or stop. If performance is not contractual, make no performance claim and disclose it as unverified rather than treating it as a preservation blocker. |
| Proposed abstraction has no demonstrated use | Prefer the simpler local design and explain why. |
| Unrelated work overlaps the target | Preserve it; isolate files and hunks without stash/reset/checkout, or ask the user when safe isolation is impossible. |

## 7. Verify and report

1. Run focused checks for the final step, then the broadest relevant verification practical for the repository.
2. Compare final results with the recorded baseline, including pre-existing failures.
3. Inspect the complete diff and status for accidental behavior changes, unrelated edits, dead code, stale comments, missed callers, exposed APIs, and excessive churn.
4. Confirm that each planned invariant has evidence. State gaps as risks rather than assuming success.
5. Report:
   - design problems addressed and concrete evidence;
   - refactorings performed;
   - behavior-preservation evidence;
   - exact tests and checks run with results;
   - pre-existing and remaining failures;
   - files intentionally changed;
   - assumptions, residual risks, and separately recommended follow-up.

Call work a refactor only when the available evidence supports preserved observable behavior. Otherwise describe it as restructuring and disclose the unverified boundary.
