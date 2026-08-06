# 5S Code Refactoring Guide

## Contents

- [Core mapping](#core-mapping)
- [Red-tag ledger](#red-tag-ledger)
- [Seiri evidence](#seiri-evidence)
- [Seiton placement rules](#seiton-placement-rules)
- [Seiso inspection rules](#seiso-inspection-rules)
- [Seiketsu standardization rules](#seiketsu-standardization-rules)
- [Shitsuke sustain rules](#shitsuke-sustain-rules)

## Core mapping

| 5S stage | Governing question | Typical software actions | Required proof |
| --- | --- | --- | --- |
| **Seiri / Sort** | Is this behavior, dependency, representation, or layer necessary? | Remove dead code, obsolete flags, unused dependencies, duplicate paths, stale compatibility layers, and unnecessary indirection. | Usage evidence, characterization, targeted tests, and contract review proportionate to risk. |
| **Seiton / Set in order** | Does every retained responsibility have one clear place and owner? | Reorganize modules, repair dependency direction, narrow APIs, rename opaque symbols, colocate tests, and separate domain from infrastructure. | Import or dependency checks, passing tests, and an explainable target structure. |
| **Seiso / Shine** | Is the touched code clean enough that abnormalities are visible? | Simplify control flow, clarify types and lifecycles, normalize error paths, remove misleading comments, and resolve local warnings. | Behavioral tests, static checks, and diff review showing reduced reasoning burden. |
| **Seiketsu / Standardize** | Is the improved state expressed as a repeatable rule? | Select consistent patterns and encode them through tools, types, tests, schemas, templates, or CI. | One clear convention applied across scope and an executable or reviewable enforcement path. |
| **Shitsuke / Sustain** | What prevents the disorder from returning? | Add regression coverage, boundary checks, ownership, CI validation, and explicit follow-up conditions. | Passing validation, a maintained guardrail, and a closed or explicitly deferred ledger. |

Use the conventional order: Seiri → Seiton → Seiso → Seiketsu → Shitsuke. Repeat the cycle on the changed area before handoff.

## Red-tag ledger

Create a working ledger before deletion or reorganization:

| Field | Meaning |
| --- | --- |
| `ID` | Stable candidate identifier. |
| `Candidate` | Symbol, file, dependency, path, abstraction, rule, or behavior under review. |
| `Concern` | Why it appears unnecessary, misplaced, dirty, inconsistent, or unsustainable. |
| `Evidence` | References, tests, configuration, runtime registration, history, benchmark, or other proof. |
| `Risk` | Tier from `refactor-risk-gates.md`. |
| `Disposition` | `KEEP`, `REMOVE`, `CONSOLIDATE`, or `DEFER`. |
| `Validation` | Check that proves the disposition did not break the contract. |

Apply these meanings strictly:

- `KEEP`: necessary or intentionally retained; state why.
- `REMOVE`: unnecessary with sufficient evidence.
- `CONSOLIDATE`: semantically equivalent behavior can safely share one implementation.
- `DEFER`: evidence is insufficient, scope excludes the change, or risk exceeds authorization.

Do not use `DEFER` as a hidden deletion queue. State the missing evidence or decision.

## Seiri evidence

Prefer multiple independent signals for medium- and high-risk deletion:

1. Static references and import graph.
2. Runtime registration, routing, dependency injection, plugin, or reflection paths.
3. Configuration, environment variables, feature flags, templates, scripts, and CI references.
4. Serialization, database, protocol, event, CLI, and public API names.
5. Tests and coverage around the candidate.
6. Public documentation and external consumers.
7. Git history showing why the candidate exists and whether compatibility is intentional.

A zero-result text search is weak evidence. It misses dynamic use, generated references, string-based lookup, reflection, and external callers.

Classify duplication by semantics, not visual similarity. Consolidate only when cases share invariants, failure modes, and reasons to change.

## Seiton placement rules

- Organize by responsibility and dependency direction before file type when repository conventions permit.
- Give each concept one canonical implementation and one obvious discovery path.
- Keep domain policy independent from delivery, storage, vendor, and framework details where the architecture supports it.
- Keep public APIs explicit and narrow; keep implementation details private.
- Colocate tests with the convention already used by the repository.
- Avoid `utils`, `helpers`, `common`, or `misc` as destinations unless the contents form a named, coherent capability.
- Do not move files merely to create symmetry. Every move must improve ownership, navigation, or dependency direction.

## Seiso inspection rules

Treat cleaning as inspection, not cosmetics:

- Make control flow and state transitions visible.
- Make units, nullability, mutability, ownership, and side effects explicit.
- Verify resource cleanup, transaction boundaries, retries, cancellation, and error propagation.
- Replace comments that narrate syntax with code that reveals intent.
- Preserve comments that explain constraints, invariants, compatibility, or counterintuitive decisions.
- Separate discovered defects from the refactor contract. Test and fix only when authorized; otherwise report them.
- Avoid broad formatting because it obscures semantic review.

## Seiketsu standardization rules

Standardize a pattern only when it is understood and valuable across the bounded scope.

Prefer enforcement in this order:

1. Language or type-system constraint.
2. Existing formatter, linter, compiler, schema, or dependency rule.
3. Focused automated test.
4. Repository template or generator.
5. Concise documentation when executable enforcement is disproportionate.

Do not add a new tool when an existing mechanism can express the rule. Do not standardize a premature abstraction merely because it looks consistent.

## Shitsuke sustain rules

Choose the lightest guardrail that catches recurrence close to its source:

- characterization or regression test;
- architectural dependency test;
- lint or type rule;
- schema or contract test;
- CI command already used by the project;
- ownership or review boundary;
- explicit expiry condition for transitional code.

Finish by repeating a small 5S pass over the final diff: remove temporary scaffolding, put new code in its proper place, clean the touched surface, verify consistency, and prove the guardrail runs.
