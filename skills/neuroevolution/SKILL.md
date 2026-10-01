---
name: neuroevolution
description: Design and run reproducible evolutionary experiments for neural controllers, learned representations, learning rules, and executable LLM agents. Use for neuroevolution, NEAT/HyperNEAT, novelty or quality-diversity search, evolution-learning hybrids, coevolution, and model-mediated evolutionary program or workflow discovery.
---

# Neuroevolution

Design a process that discovers capable systems through variation, execution, selection, and retained alternatives. This package has two equal tracks: evolving actual neural systems, and evolving executable agents around language models. Operate the bundled toolkit; keep method identity and measured evidence explicit.

## Frame the experiment

Identify the system being discovered, its genome and executable decoder, the environment/task distribution, objectives, behavioral descriptors, constraints, learning/inheritance semantics, and resource limits. Distinguish the optimization metric from what would constitute useful progress on unseen conditions. Freeze comparative cases, seeds, metrics and budgets before running comparisons.

Start from a compatible example and adapt it to the user's question. The included domains are small executable reference environments, not a claim of arbitrary-task support. Extending to a new domain requires an evaluator/decoder implementation and a mechanism test. A representation described in prose is not an implemented encoding.

Read [the book-to-capability map](references/book-to-capability.md) for mechanism identity, adaptations, tests and reproducible examples. Historical raw evaluation data is retained locally and is not distributed. Choose technical guidance as needed:

| Question | Read |
| --- | --- |
| Weight optimization, fitness, Pareto, novelty, NSLC or MAP-Elites? | [Population search](references/search.md) |
| Topology, CPPNs, HyperNEAT, modular architecture search? | [Structural evolution](references/structural.md) |
| Lifetime learning, inheritance, initialization, ERL, DQD, plasticity or tiny-model tensors? | [Learning and models](references/learning.md) |
| Team/opponent dependence, changing environments, transfer or learned surrogates? | [Ecology](references/ecology.md) |
| Prompts, bounded workflows, programs, language-model variation, or a neural router? | [LLM experiments](references/llm.md) |
| Installation, configuration, checkpointing, reports or extending the toolkit? | [Operation and contracts](references/operation.md) |
| CPU versus GPU execution, batching, CUDA/MPS setup or measured throughput? | [Accelerator execution](references/accelerators.md) |

## Execute through the shared interface

From this skill directory, use Python 3.12 and `uv sync --frozen`. The dependency lock includes a CPU-only Linux PyTorch source and an immutable NEAT source archive. `uv run --frozen neuroevo doctor` checks actual imports and Docker availability. Read its results before choosing a capability.

For tensor execution, select `[compute] backend="torch"` with an explicit `device="cpu"`, `"mps"`, or `"cuda"`. Read the accelerator reference first: supported profiles have different batching behavior, and CUDA uses its own locked environment. Unavailable devices and unsupported local accelerator profiles are errors. Keep the CPU reference as a reproducible baseline and measure speed rather than inferring it from device placement.

```bash
uv run --frozen neuroevo validate examples/neat-xor.toml
uv run --frozen neuroevo run examples/neat-xor.toml --out /absolute/path/to/new-run
uv run --frozen neuroevo inspect /absolute/path/to/new-run
uv run --frozen neuroevo replay /absolute/path/to/new-run --seed 10000
uv run --frozen neuroevo report /absolute/path/to/new-run
```

Check example filenames before selecting one. Runs write only into the requested output directory. Use `resume RUN` after interruption or a completed bridge response; never delete evidence to make a failed experiment look successful. A budget-exhausted run is partial evidence. Expanding a frozen comparison requires a new declared protocol, not editing results or silently increasing limits.

Defaults are serial local CPU reference execution, 512 evaluation dispatches and 600 active seconds, with an upper bound of four workers. Supported torch profiles batch numerical work within one orchestration process. Each profile reports its actual interactions, learning work and model usage where observable. A dispatched failed candidate consumes budget, including every dispatched member of a failed tensor batch. Surrogate predictions and true evaluations have separate evidence labels.

For a model request, use `bridge next RUN`, read its exact messages, produce the requested response, save it as a text file, then `bridge submit RUN ID --response FILE --provenance 'truthful model/host identity'` and `resume RUN`. The bridge never invokes another agent itself. Do not programmatically manufacture benchmark responses and describe them as live inference. Protocol fixtures and real host-agent responses have separate evidence.

Hosted endpoints require explicit spending limits and configured prices. Use local endpoints or the host bridge for initial experiments. Evolved Python programs require the documented no-network Docker sandbox. Checkpoints are trusted-local pickle state; do not load third-party checkpoint files.

## Inspect and interpret discoveries

Preserve saved candidates, populations, ancestry, optimizer/learner state, archives/species, seeds and source identities in local output directories outside Git. Exercise replay on unseen conditions. For LLM agents, use `evaluate-heldout TRAIN_RUN --out NEW_RUN --seed 10000`, then service its fresh bridge requests; stored response replay is not held-out inference.

Include an actual explanatory figure from the report: trajectories, occupied behavioral space, network/generated connection diagrams or learning curves. Describe what was measured, the relevant baseline, costs, failures and uncertainty. Use five independent experiment seeds for stochastic comparisons; report seed variation and unobserved model randomness honestly. A valid negative result is useful.

Keep three claims separate: algorithm correctness, successful operation through the skill, and comparative performance in the tested domain. Installation in an agent client establishes package discovery, not successful operation. Small neural/language-model demonstrations do not establish pretrained large-LLM effectiveness. Bounded POET progress does not establish unlimited open-ended discovery.

Report unsupported compositions directly. Neural NEAT and NEAT-inspired workflow graphs are different methods; this release does not relabel prompt editing as NEAT. ERL requires shared experience and actor reinsertion. HyperNEAT requires CPPN coordinate queries that generate actual weights. Inherited versus reset learned state must be declared. Measured confirmation, rather than a surrogate prediction, determines a final candidate's accepted performance.
