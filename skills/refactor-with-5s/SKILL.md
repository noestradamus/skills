---
name: refactor-with-5s
description: Systematically audit and refactor an existing codebase with the Japanese 5S sequence—Seiri (Sort), Seiton (Set in order), Seiso (Shine), Seiketsu (Standardize), and Shitsuke (Sustain)—while preserving intended behavior and proving safety with tests. Use when the user asks to refactor, clean up, reorganize, simplify, de-duplicate, remove dead code, reduce technical debt, standardize patterns, or improve maintainability. Do not use for feature-first implementation, greenfield architecture, broad rewrites, dependency upgrades, or standalone bug fixing unless refactoring is the primary task.
---

# Refactor with 5S

## Overview

Turn a cluttered, inconsistent, or fragile code area into a simpler and more sustainable system without silently changing its intended behavior.

Apply 5S as an ordered, evidence-gated refactoring loop rather than attaching five labels to changes after the fact:

1. **Seiri / 整理 / Sort** — distinguish necessary code from waste.
2. **Seiton / 整頓 / Set in order** — give every retained responsibility a clear place.
3. **Seiso / 清掃 / Shine** — clean while inspecting for hidden abnormalities.
4. **Seiketsu / 清潔 / Standardize** — encode the improved state as repeatable standards.
5. **Shitsuke / 躾 / Sustain** — add discipline and guardrails that prevent regression.

Read [references/5s-refactoring-guide.md](references/5s-refactoring-guide.md) before classifying or changing candidates. Read [references/refactor-risk-gates.md](references/refactor-risk-gates.md) before deleting code, changing public contracts, moving data boundaries, or touching high-risk logic. Use [references/refactor-report-template.md](references/refactor-report-template.md) for the final handoff.

## Operating contract

- Treat refactoring as behavior-preserving unless the user explicitly authorizes a behavior or contract change.
- Inspect repository instructions first, including `AGENTS.md`, `CONTRIBUTING`, build files, CI workflows, formatter and linter configuration, architecture notes, and package-level guidance.
- Establish and record a baseline before editing. Separate pre-existing failures from regressions introduced by the refactor.
- Preserve uncommitted user work. Never discard, overwrite, reset, or reformat unrelated changes.
- Choose the smallest coherent scope that contains the requested problem. Do not refactor the entire repository merely because the request is broad.
- Keep each change reviewable. Avoid mixing refactoring with new features, dependency upgrades, broad formatting, or unrelated bug fixes.
- Prefer repository-native tools and commands over inventing new infrastructure.
- Change source generators rather than generated output. Treat migrations, lockfiles, vendored code, snapshots, schemas, and public interfaces as protected artifacts unless the task explicitly includes them.
- Never push, merge, deploy, or publish unless the user explicitly requests it. Follow any repository-specific commit instructions.
- Record uncertainty instead of disguising it. Defer candidates that cannot be proved safe.

## Select the operating mode

Choose one mode from the request and repository state:

- **Audit mode** — inspect, classify, and propose a 5S plan without modifying code when the user asks for an assessment, review, or plan.
- **Execute mode** — perform the bounded refactor when the user asks to clean, reorganize, simplify, or refactor code. Use this by default for an implementation request.
- **Recovery mode** — use when the baseline is already failing. Isolate pre-existing failures, add characterization where possible, and avoid broad changes that cannot be distinguished from existing breakage.

State the selected mode, scope, invariants, and explicit exclusions before making material changes.

## Workflow

### 1. Establish the refactor contract

1. Identify the requested target: files, module, package, subsystem, concern, or repository-wide pattern.
2. Define observable invariants that must remain unchanged, including relevant APIs, data formats, error semantics, side effects, ordering, timing, persistence, authorization, and user-visible behavior.
3. Identify allowed changes and explicit non-goals.
4. Discover the repository's test, lint, type-check, build, benchmark, and formatting commands from project configuration rather than guessing.
5. Inspect Git branch and status. Note existing modifications and keep the refactor isolated from them.
6. Assign an initial risk tier using [references/refactor-risk-gates.md](references/refactor-risk-gates.md).

### 2. Observe the code gemba and capture the baseline

Inspect the actual code path before prescribing a target architecture.

1. Trace entry points, call paths, imports, data flow, side effects, configuration, tests, and runtime boundaries.
2. Run the narrowest meaningful existing checks first, then broader checks when practical.
3. Record every baseline command and result, including failures that existed before the refactor.
4. Measure only signals that help the decision, such as duplicated logic, dependency direction, file or function size, warning counts, complexity hotspots, or test coverage around the target.
5. Create a working **red-tag ledger** for questionable code. Give every candidate a disposition: `KEEP`, `REMOVE`, `CONSOLIDATE`, or `DEFER`.

Do not begin with file movement or mass deletion. First understand what the code does and what proves that behavior.

### 3. Seiri — Sort

Separate necessary behavior from waste.

1. Inventory dead code, unused symbols, obsolete flags, duplicate paths, abandoned adapters, redundant dependencies, stale comments, expired compatibility layers, and unnecessary indirection.
2. Prove usage or non-usage through multiple forms of evidence where risk warrants it: code references, import graphs, tests, configuration, runtime registration, public documentation, serialized names, reflection, plugin discovery, and Git history.
3. Remove only candidates whose behavior is demonstrably unnecessary within the agreed contract.
4. Consolidate true duplication only after confirming that the duplicated cases share the same semantics and change reasons.
5. Add characterization tests before removing or consolidating uncertain legacy behavior.
6. Mark unresolved candidates `DEFER` with the missing evidence and next action. Do not guess.
7. Run targeted checks after each coherent removal batch.

Do not optimize for the largest deletion count. Optimize for the clearest verified reduction in waste.

### 4. Seiton — Set in order

Arrange retained code around clear responsibilities and dependency direction.

1. Define the target placement and ownership of each retained responsibility before moving files.
2. Put entry points, domain logic, infrastructure, adapters, tests, configuration, and shared primitives in predictable locations consistent with repository conventions.
3. Rename private symbols and modules when names obscure responsibility, lifecycle, units, or side effects.
4. Reduce accidental public surface area. Keep APIs narrow and explicit.
5. Repair imports, call sites, test locations, and documentation atomically with each move.
6. Prefer cohesive modules over generic dumping grounds such as `utils`, `helpers`, or `common` without a clear domain.
7. Avoid speculative abstraction. Extract a shared abstraction only when it reduces demonstrated duplication without erasing meaningful differences.
8. Run structural and targeted behavioral checks after each move batch.

### 5. Seiso — Shine

Clean the touched area while inspecting it for abnormalities.

1. Simplify control flow, nesting, branching, state transitions, and error paths without changing intended outcomes.
2. Clarify names, types, units, ownership, nullability, mutability, and resource lifecycles.
3. Remove misleading comments and replace only those that explain non-obvious intent, invariants, or constraints.
4. Make cleanup, error handling, logging, retries, cancellation, and transaction boundaries explicit where they are currently hidden or inconsistent.
5. Eliminate local lint, type, and compiler warnings caused by or directly adjacent to the refactor.
6. Inspect every cleaned area for latent defects. When a likely bug appears, add a regression test and fix it only if it is inside the authorized scope; otherwise record it separately.
7. Avoid repository-wide formatting or cosmetic churn unrelated to the target.

A cleaner-looking diff is insufficient. The code must become easier to reason about and inspect.

### 6. Seiketsu — Standardize

Convert the improved local state into an explicit, repeatable standard.

1. Select one repository-consistent pattern for each repeated concern within scope.
2. Apply the pattern consistently across the bounded area, not selectively to the easiest files.
3. Encode important rules in executable controls where proportionate: formatter, linter, type system, tests, schema validation, dependency-boundary checks, templates, or CI.
4. Standardize interfaces, error handling, naming, module boundaries, test structure, and observability only where the repository benefits from one clear convention.
5. Remove temporary shims when safe. Otherwise record owner, reason, and removal condition rather than leaving an indefinite compatibility layer.
6. Prefer a small enforceable standard over a large prose convention nobody can verify.

### 7. Shitsuke — Sustain

Make the refactor durable.

1. Add or strengthen regression tests for the behavior and boundaries the refactor relies on.
2. Add the lightest effective guardrail that prevents the same disorder from returning.
3. Ensure CI or the repository's normal validation path exercises the relevant guardrail when appropriate.
4. Re-run targeted checks, then the broadest practical relevant suite.
5. Inspect the complete diff for accidental API, data, security, performance, or behavior changes.
6. Revisit the red-tag ledger. Resolve supported candidates and preserve deferred candidates with explicit evidence gaps.
7. Perform one final 5S pass over the changed area. Remove temporary scaffolding, stale aliases, unused tests, and comments created during the refactor.
8. Leave the working tree, branch, and commit state exactly as requested by the user.

### 8. Verify and hand off

1. Run `git diff --check` or the repository-equivalent whitespace validation.
2. Run the discovered formatter check, linter, type checker, tests, build, and relevant benchmarks in the order justified by scope and cost.
3. Compare results with the baseline. Do not report a pre-existing failure as a regression or a passing targeted test as proof of the entire system.
4. Review the diff by concern. Confirm that complexity was removed rather than relocated behind a more obscure abstraction.
5. Report results with [references/refactor-report-template.md](references/refactor-report-template.md).
6. Distinguish clearly between:
   - refactor implementation completed;
   - automated validation passed or failed;
   - developer manual acceptance completed or pending;
   - merge, stakeholder, production, or deployment approval, which must never be implied without evidence.

## Risk gates

Apply stronger proof as risk increases. Defer rather than force unsafe progress.

Stop removal, movement, or consolidation when any of the following remains unresolved:

- usage may occur through reflection, dependency injection, registration, serialization, dynamic imports, templates, external callers, or generated code;
- a public API, schema, protocol, migration, persistence format, authorization rule, concurrency behavior, numerical result, or error contract may change;
- critical behavior lacks both tests and a reliable characterization path;
- uncommitted user changes overlap the target in a way that cannot be preserved safely;
- the refactor would require a broad rewrite to remain coherent;
- the proposed abstraction hides different semantics or likely future change reasons;
- validation cannot distinguish the new result from an already-broken baseline.

Use [references/refactor-risk-gates.md](references/refactor-risk-gates.md) to decide the required evidence and response.

## Completion criteria

Declare the 5S refactor complete only when all applicable conditions hold:

- The agreed behavior and contracts are unchanged, or every intentional change is explicitly authorized and tested.
- No baseline check regressed without a documented and accepted reason.
- Every deleted or consolidated item has evidence supporting its disposition.
- The changed structure has clearer ownership and dependency direction.
- Local complexity, duplication, or ambiguity was reduced rather than merely moved.
- The resulting pattern is consistent across the agreed scope.
- At least one proportionate sustain mechanism protects the improved state.
- The final report names commands run, results, deferred candidates, residual risks, and manual checks still required.
- Git operations match the user's instructions; no push, merge, deploy, or approval is assumed.

## Common mistakes

- Treating 5S as formatting, naming, or folder cleanup only.
- Deleting code because a single text search found no references.
- Moving files before understanding behavior and dependencies.
- Replacing several small duplicates with one over-general abstraction.
- Introducing a new framework, tool, or configuration larger than the disorder it prevents.
- Combining refactoring with feature work, dependency upgrades, or repository-wide formatting.
- Fixing a newly discovered bug silently and calling the whole change behavior-preserving.
- Reporting success after one narrow test while broader relevant checks remain unrun.
- Describing a standard without encoding or enforcing it.
- Ending after cleanup without Shitsuke guardrails and a final regression pass.
