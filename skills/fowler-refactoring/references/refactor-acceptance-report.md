# Refactor Acceptance Report

Use this template for large, high-risk, campaign-style, or formally reviewed refactoring work. Omit inapplicable fields, but never merge distinct acceptance states or imply approval without evidence.

## 1. Scope and contract

- **Mode:** Audit / Refactor / Recovery
- **Target:**
- **Requested outcome:**
- **Observable invariants:**
- **Allowed changes:**
- **Explicit exclusions:**
- **Risk:** Low / Medium / High
- **Repository instructions followed:**

## 2. Baseline

| Command or inspection | Pre-refactor result | Classification and notes |
| --- | --- | --- |
|  |  |  |

Record pre-existing failures, unstable checks, blocked commands, and environment limits separately.

## 3. Problems and transformations

| Problem and evidence | Transformation | Preserved invariant | Verification | Rollback boundary |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |

List separately authorized bug fixes, features, migrations, or optimizations as behavior changes rather than refactorings.

## 4. Red-tag ledger when used

| ID | Candidate | Concern | Evidence | Risk | Disposition | Validation |
| --- | --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |  |

For every `DEFER`, state the missing evidence or authorization and the next action.

## 5. Standardization and sustainment when used

- **Repeated concern addressed:**
- **Selected standard and bounded scope:**
- **Existing enforcement reused:**
- **New authorized enforcement added:**
- **Sustain mechanism:**
- **Transitional code owner and removal condition:**
- **Reason no new guardrail was warranted, if applicable:**

## 6. Verification

| Command or review | Post-refactor result | Baseline comparison |
| --- | --- | --- |
|  |  |  |

- **Focused behavior evidence:**
- **Broader checks:**
- **Checks not run and reason:**
- **Manual scenarios still required:**

## 7. Acceptance state

- **Refactor implementation:** Completed / Partial / Not started
- **Automated validation:** Passed / Failed / Partial / Not run
- **Developer manual acceptance:** Completed / Pending / Not applicable
- **Stakeholder or domain approval:** Completed / Pending / Not requested
- **Merge readiness:** Ready / Blocked / Not assessed
- **Production or deployment approval:** Approved / Not approved / Not assessed

Claim only states supported by current evidence. Automated validation does not imply manual acceptance, merge approval, or production approval.

## 8. Residual risk and deferred work

- **Remaining uncertainty:**
- **Deferred candidates and missing evidence:**
- **Suspected defects reported separately:**
- **Recommended follow-up:**

## 9. Git state

- **Branch:**
- **Commits created:**
- **Push or merge performed:**
- **Remaining working-tree changes:**
