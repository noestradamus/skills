# Refactoring Campaigns

Use this reference for subsystem or repository hygiene, multi-candidate cleanup, repeated-pattern standardization, or recurrence prevention. These are operational governance extensions, not Fowler catalog techniques.

## Contents

- [Keep the campaign bounded](#keep-the-campaign-bounded)
- [Use the red-tag ledger](#use-the-red-tag-ledger)
- [Decide with evidence](#decide-with-evidence)
- [Standardize the bounded scope](#standardize-the-bounded-scope)
- [Sustain the improved state](#sustain-the-improved-state)
- [Close the campaign](#close-the-campaign)

## Keep the campaign bounded

Use a campaign when several related candidates need coordinated inspection, removal, consolidation, reorganization, or standardization. Do not create one for a single rename, extraction, move, or conditional simplification.

Before editing:

1. Name the subsystem, module set, concern, and explicit exclusions.
2. Define the observable contract and the reason this group should be handled together.
3. Record the baseline and select Refactor or Recovery mode.
4. State the campaign's completion condition; do not use “clean everything.”

When the user requests only an audit or plan, populate the ledger and recommendations without changing code.

## Use the red-tag ledger

Track every candidate that requires a disposition:

| Field | Required content |
| --- | --- |
| `ID` | Stable identifier used in plans and reports |
| `Candidate` | Symbol, file, dependency, path, abstraction, rule, or behavior under review |
| `Concern` | Why it appears unnecessary, duplicated, misplaced, inconsistent, or likely to recur |
| `Evidence` | References, tests, configuration, runtime registration, history, benchmark, or contract evidence |
| `Risk` | `low`, `medium`, or `high` using the rubric in `SKILL.md` |
| `Disposition` | `KEEP`, `REMOVE`, `CONSOLIDATE`, or `DEFER` |
| `Validation` | Check that can show the disposition preserved the agreed contract |

Apply the dispositions strictly:

- **KEEP:** The candidate is necessary or intentionally retained. Record why.
- **REMOVE:** Sufficient evidence shows the candidate is unnecessary within the supported contract.
- **CONSOLIDATE:** The cases have equivalent semantics, compatible invariants, and compatible reasons to change.
- **DEFER:** Evidence is insufficient, scope excludes the change, or risk exceeds authorization. Record the missing evidence or decision and the next action.

Never use `DEFER` as a hidden deletion queue. Never optimize for the largest removal count.

## Decide with evidence

- For removal, follow [Remove Dead Code](refactoring-catalog.md#remove-dead-code) and its dynamic-use checks.
- For consolidation, use the [duplication-removal verification](verification-strategies.md#duplication-removal) and extract only the genuinely shared primitive when cases differ.
- For movement and renaming, follow the relevant catalog entry and inspect dependency direction, dynamic names, and published boundaries.
- Escalate a small-looking candidate when it touches a high-risk contract. Diff size does not determine risk.
- Keep uncertain behavior rather than forcing a disposition that cannot be verified.

## Standardize the bounded scope

Standardize only an understood repeated concern whose inconsistency has demonstrated cost. Select one repository-consistent pattern and apply it across the agreed scope, not just the easiest files.

Prefer enforcement in this order:

1. Language or type-system constraint.
2. Existing formatter, linter, compiler, schema, or dependency-boundary rule.
3. Focused automated test.
4. Existing template or generator.
5. Concise documentation when executable enforcement is disproportionate.

Do not add a tool, configuration rule, dependency, or CI job without authorization. Do not standardize a premature abstraction merely because uniformity looks cleaner.

## Sustain the improved state

Use the lightest mechanism that catches the demonstrated recurrence near its source:

- characterization, regression, contract, or boundary test;
- existing lint, type, schema, or dependency rule;
- existing CI command that already covers the relevant check;
- ownership or review boundary;
- explicit owner and expiry/removal condition for transitional code.

Add or strengthen a guardrail only when its maintenance cost is proportionate to the recurrence risk. For a trivial local refactor, recording that no new guardrail is warranted may be the correct outcome.

## Close the campaign

1. Reconcile every ledger entry and preserve the evidence for each disposition.
2. Remove temporary scaffolding, stale shims, aliases, tests, comments, and instrumentation created solely for the work, unless they now serve a documented purpose.
3. Confirm that any selected standard is consistent across the agreed scope and that its enforcement actually runs.
4. Run focused and broad verification according to risk, then review the complete diff.
5. Use [the acceptance report](refactor-acceptance-report.md) and keep implementation, validation, human acceptance, merge readiness, and production approval distinct.
