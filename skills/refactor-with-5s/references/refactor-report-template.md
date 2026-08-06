# 5S Refactor Report Template

Use this structure for a completed audit or implementation. Omit inapplicable fields, but never merge distinct acceptance states.

## 1. Scope and contract

- **Mode:** Audit / Execute / Recovery
- **Target:**
- **Behavioral invariants:**
- **Allowed changes:**
- **Explicit exclusions:**
- **Risk tier:**
- **Repository instructions followed:**

## 2. Baseline

| Command or inspection | Pre-refactor result | Notes |
| --- | --- | --- |
|  |  |  |

List pre-existing failures separately from a clean baseline.

## 3. 5S changes

### Seiri — Sort

- Removed:
- Consolidated:
- Kept intentionally:
- Deferred:
- Evidence used:

### Seiton — Set in order

- Moves or renames:
- Responsibility or ownership clarified:
- Dependency direction improved:
- Public surface affected:

### Seiso — Shine

- Complexity simplified:
- Types, names, errors, resources, or comments clarified:
- Latent defects found:
- Behavior-changing fixes, if explicitly authorized:

### Seiketsu — Standardize

- Pattern selected:
- Scope standardized:
- Executable enforcement added or reused:

### Shitsuke — Sustain

- Regression tests or guardrails:
- CI or routine validation path:
- Transitional code and expiry condition:
- Final 5S pass result:

## 4. Red-tag ledger

| ID | Candidate | Concern | Evidence | Risk | Disposition | Validation |
| --- | --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |  |

## 5. Verification

| Command or review | Post-refactor result | Baseline comparison |
| --- | --- | --- |
|  |  |  |

State checks not run and the reason. Do not generalize from a narrower check.

## 6. Acceptance state

- **Refactor implementation:** Completed / Partial / Not started
- **Automated validation:** Passed / Failed / Partial / Not run
- **Developer manual acceptance:** Completed / Pending / Not applicable
- **Stakeholder or domain approval:** Completed / Pending / Not requested
- **Merge readiness:** Ready / Blocked / Not assessed
- **Production or deployment approval:** Approved / Not approved / Not assessed

Only claim a state supported by evidence.

## 7. Residual risk and deferred work

- Remaining uncertainty:
- Deferred red tags and missing evidence:
- Manual scenarios still required:
- Follow-up that should remain separate from this refactor:

## 8. Git state

- **Branch:**
- **Commits created:**
- **Push or merge performed:**
- **Remaining working-tree changes:**
