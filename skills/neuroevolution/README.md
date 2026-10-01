# Neuroevolution

A portable agent skill and executable Python toolkit for evolving neural systems
and executable LLM agents. It includes canonical mechanisms, small reference
environments, runnable examples and tools for saving and replaying experiments.

Inspired by *Neuroevolution: Harnessing Creativity in AI Agent Design* by
Sebastian Risi, Yujin Tang, David Ha, and Risto Miikkulainen.

The built-in examples run immediately after setup. A new application domain needs
its own evaluator/representation adapter and mechanism checks. Supported method
combinations are explicit; successful experiments do not guarantee superiority.

**Release scope: experimental reference laboratory.** The mechanisms operate on
small built-in domains. This is useful for studying, testing and extending
neuroevolution; it is not yet a general optimizer for arbitrary tasks or evidence
of large-model effectiveness. Small-domain comparisons have mixed or negative
results, and the live LLM tasks have reached ceiling scores that cannot establish
an improvement from evolution. Passing mechanism tests does not establish practical
superiority on a new task.

## First neural experiment

Use Python 3.12 and uv. From this directory:

```bash
uv sync --frozen
uv run --frozen neuroevo doctor
uv run --frozen neuroevo run examples/ga-xor.toml --out runs/first
uv run --frozen neuroevo replay runs/first --seed 10000
uv run --frozen neuroevo report runs/first
```

Open `runs/first/report.md`. The output directory also holds the configuration,
environment identity, candidate evidence, journal, figures and trusted-local
checkpoint. `resume` continues an interrupted run with its original budget.

Through an agent, ask: “Use neuroevolution to run the NEAT CartPole example,
replay the saved controller under unseen conditions, and explain the evidence.”

## CPU and GPU execution

The CPU reference remains the default. Apple GPU examples use the same environment:

```bash
uv run --frozen neuroevo validate examples/accelerators/gradient-mps.toml
uv run --frozen neuroevo run examples/accelerators/gradient-mps.toml --out runs/mps-learning
```

Linux x86-64 NVIDIA GPU users use the separate CUDA environment:

```bash
uv sync --project environments/cuda --frozen
uv run --project environments/cuda --frozen neuroevo doctor
uv run --project environments/cuda --frozen neuroevo run examples/accelerators/gradient-cuda.toml --out runs/cuda-learning
```

Device placement is explicit, unsupported combinations fail, and CPU fallback is
not automatic. Population batching covers controller evaluation, structural
phenotypes, dense inner learning and tiny-model evaluation. ERL, plasticity, DQD
and NAS have narrower device support. See the [matrix, verification scope and
limitations](references/accelerators.md).

## First LLM-agent experiment

```bash
uv run --frozen neuroevo run examples/llm-workflow.toml --out runs/workflow
uv run --frozen neuroevo bridge next runs/workflow
```

The run pauses for real model responses. The operating agent reads the request,
writes its response to a file, submits it with `bridge submit`, and resumes. A
configured local/hosted endpoint can supply responses automatically instead.
See the exact commands in [LLM experiments](references/llm.md). Paid endpoints
require explicit spending configuration. Generated programs additionally require
Docker. Model-server inference hardware is independent of this runner's device.

Through an agent, ask: “Use neuroevolution to run the workflow example through
the host-agent bridge, freeze the winner, and evaluate held-out cases.”

## Scope and verification

- [Skill instructions](SKILL.md): method choice and the operating workflow.
- [Operation reference](references/operation.md): CLI/API, extension contracts and budgets.
- [Book-to-capability map](references/book-to-capability.md): defining mechanisms and disclosed adaptations.
- [Mechanism tests](tests/): assertions about algorithm behavior, persistence and execution.
- [Examples](examples/) and [experiment scripts](scripts/): generate new measurements, reports and replayable runs locally.

Run `uv run --frozen pytest -q` for the test suite; hardware-dependent checks may
skip on unavailable devices. The method references identify the corresponding
examples and comparison scripts. Historical raw evaluation data is retained
locally and is not distributed with the repository. Generated runs and reports
belong in ignored local output directories such as `runs/` or outside the checkout.
Keep algorithm correctness, successful operation and comparative performance
as separate claims when interpreting your own results.

Defaults are 512 evaluation dispatches and 600 active seconds. The orchestration
process is single-threaded at the experiment level; tensor batches provide
parallel numerical work. The environments and language models are small reference
tasks, not industrial reproductions. Windows and other agent-client runtime
behavior are not established by installation checks. Distributed execution,
production multi-tenant isolation and automatic cross-device checkpoint migration
are outside the current implementation.
