---
name: pushing-research-frontier
description: Use when planning, executing, or evaluating research intended to surpass the strongest current method, establish a new state of the art, or make a defensible world-best claim.
---

# Pushing Research Frontier

## Overview

Aim for a demonstrable new frontier, not a convenient improvement. Pair maximal ambition with strict evidence: a claimed win is invalid until it survives reproduction, controlled comparison, ablation, statistical scrutiny, stress testing, and reproducibility review.

Read [references/mindset.md](references/mindset.md) when designing a research program, reviewing experimental evidence, or deciding whether a result is ready to claim.

## Workflow

1. Define the claim, target benchmark, constraints, and strongest relevant evaluation setting.
2. Map the current frontier from fresh evidence. Identify the actual leader, margin, setup, code, and unresolved weaknesses. Label any unverified frontier facts explicitly.
3. Reproduce the strongest baseline on the exact setup before claiming an improvement. Investigate any reproduction gap.
4. Decompose and ablate the incumbent. Identify load-bearing components, assumptions, and failure modes.
5. Generate at least three plausible directions before committing. Include at least one assumption-breaking or cross-domain direction absent from the established approach.
6. Run the cheapest controlled experiment that could disprove each direction. Record hypothesis, setup, result, and learning.
7. Advance only evidence-backed candidates. Compare under identical conditions with fixed seeds, multiple trials, variance, and confidence intervals.
8. Ablate the new method, stress-test generality, version the environment and data, and document reproduction steps.
9. Claim only what the evidence proves. Treat the new best result as the next baseline and continue searching.

## Quick Reference

| Stage | Required evidence |
| --- | --- |
| Frontier mapping | Fresh sources, leader, margin, setup, weaknesses |
| Baseline | Reproduced result on the exact setup |
| Candidate selection | Three directions, including one nonstandard direction |
| Experiment | Controlled falsification test and experiment ledger |
| Win claim | Strongest baseline, repeated trials, uncertainty, ablations |
| Release | Robustness checks and reproducible procedure |

## Common Mistakes

- Treating a famous baseline as the frontier instead of verifying the current leader.
- Comparing against reported numbers without reproducing the baseline.
- Tuning the new method more heavily than the incumbent.
- Presenting one preferred idea without generating alternatives.
- Calling noise, a single seed, or a cherry-picked dataset a win.
- Stopping at a publishable improvement when the stated objective is a frontier result.
