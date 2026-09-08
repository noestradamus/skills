---
name: research-to-runnable
description: Turn a computational problem, research paper, or method repository into one runnable pilot that informs a practical decision. Use for trying or adapting ML methods, algorithms, and numerical or scientific approaches in a project, including focused method selection when none is chosen. Not for literature summaries alone, routine implementation without a research question, or a full frontier research campaign.
---

# Research to Runnable

Choose the smallest experiment that can answer the question while preserving the mechanism being tested. Deliver the implementation, the evidence, and a useful next decision. A valid negative result is a successful pilot.

## Follow the requested endpoint

Default to one practical adoption pilot: select or understand a method, adapt it to the project, implement it, run a bounded comparison, and interpret the result. Explicit planning-only, implementation-only, faithful-reproduction, or analysis-of-existing-results requests set a different endpoint; do not expand them into execution or new trials.

Use ordinary language and available context, not a required intake form. Accept a paper, method, repository, or concrete computational problem. Recover project, data, objective, and resource context from the conversation and relevant artifacts before asking. Ask only when an unresolved choice would materially change the work.

For an explicit new-best or state-of-the-art objective, retain the broader evidence requirements of `pushing-research-frontier` when that skill is available. This skill can supply a bounded pilot within that program; a local pilot alone does not establish a frontier claim. Ordinary adoption work does not require frontier mapping or a full ablation campaign.

## Establish what the pilot should decide

Inspect the actual project and data semantics alongside the source: existing baselines, evaluation harness, splits, dependencies, prior results, and usable compute. Recheck remembered execution state before relying on it. Preserve unrelated work and existing evidence; choose isolation appropriate to the checkout and task rather than restructuring the project.

Frame a decision, such as whether an approach improves the required forecast, reaches an error tolerance at lower cost, or fits a memory limit. Name the target conditions and what an informative result would change.

If a method is supplied, evaluate it. If only a problem is supplied, make a focused comparison of plausible approaches and select one for fit, testability, and effort. Use primary sources for consequential method claims. Do not turn selection into an exhaustive survey or require an arbitrary number of alternatives.

Identify the method's essential mechanism, required inputs, assumptions, objective, and evaluation conditions. Trace material choices to the relevant paper sections, official specifications, or code revision. Distinguish faithful reproduction, adaptation to new conditions, and a simplified surrogate. Record material departures and why they matter. Resolve consequential paper/code conflicts against the requested question; neither source silently overrides the other. If a detail is inaccessible or ambiguous, retain the uncertainty and determine whether it prevents a valid test.

## Commit to an informative comparison

Read the relevant sections of [comparison-design.md](references/comparison-design.md) when designing or assessing the pilot. It covers reduction, predictive ML, numerical accuracy, algorithm timing, and uncertainty.

Before observing comparative outcomes, record a short experiment plan in the project's normal notes or equivalent artifact:

- The question, candidate, credible comparator or analytical reference, and target conditions.
- The evaluation cases and relevant independence boundaries, primary measure, and decision criterion.
- What must survive any reduction in data, resolution, iterations, or model size.
- The execution envelope: available resources, practical runtime or work bound, planned repetitions or tuning, and any early stopping rule.

Use a numerical criterion when it is justified. Otherwise state a provisional criterion and its limits without inventing a required percentage gain. This record is a commitment against moving the goal after seeing results, not an extra approval checkpoint. Reuse existing authorization. Derive bounds from the task and available evidence; ask only when a consequential resource or objective choice remains unresolved.

Reduce work only while preserving the phenomenon being tested. Synthetic data can establish an analytical property or isolate a mechanism; explain its relevance to the target problem. If the affordable setup cannot answer the target question, state the smaller question it can answer. A feasibility check leaves effectiveness unresolved. If even that would be misleading, finish useful preparation and identify the missing prerequisite.

## Implement, verify, and run

Use the project's native code, configuration, environment, and experiment tools. Add the minimum implementation needed for this pilot; avoid a new runner framework or tracking schema. Retain source, data-selection, environment, and configuration identities sufficient to reproduce the actual run, including local modifications that affect it. Reuse existing manifests and logs where sufficient.

Check the defining implementation behavior before interpreting comparative performance: for example an analytical case, invariant, trusted reference output, or mechanism-specific test. Verify the comparator too. A successful import, output shape, or completed training loop alone is not evidence that the method was implemented correctly.

Run the declared comparison and necessary checks within the task's envelope. Keep measured outputs and failures. Repair a diagnosed execution defect when there is a concrete reason the next attempt should differ; do not keep retrying an unchanged blocker. Runtime failure is not evidence against the scientific method. Missing weights or unavailable hardware do not justify silently substituting an untrained model or a surrogate and calling it the original experiment.

When a defect invalidates earlier measurements, retain them as invalidated evidence and record the correction. Changed hypotheses, post-result tuning, or changed evaluation criteria belong to an explicitly identified follow-up, not a retroactive successful pilot. Complete the declared comparison unless a stopping rule specified beforehand applies or a validity or resource blocker prevents continuation. Do not stop planned repetitions because an early outcome looks favorable.

## Deliver evidence and a decision

For an executed pilot, deliver project-native runnable code/configuration, its logs and metrics, and one concise experiment note. Adapt the note to the work rather than emitting empty template sections. Include:

- The decision and comparison actually performed, sources, and consequential adaptations.
- Measured results and relevant accuracy, runtime, memory, or other tradeoffs; link raw evidence instead of duplicating it.
- Separate statements of implementation validity, comparison validity, and what the result supports. Report relevant uncertainty or what could not be measured.
- Reproduction commands with working directory, prerequisites, inputs/configuration identities, and expected outputs. Mark commands that have not been exercised.
- A recommendation under the tested conditions and the next evidence that would change it.

A completed valid pilot may support proceeding, declining, or collecting more evidence. An inconclusive result can complete the planned pilot without settling the wider question. A blocked execution is partial completion: say what is implemented or checked, what has not run, and the exact prerequisite and continuation step. Distinguish observed findings from estimates and proposed work.

Finish at the requested endpoint. Do not continue searching methods, seeds, metrics, or cases to obtain a favorable result. Broader research, production integration, publication, and resource expansion follow the user's subsequent direction.
