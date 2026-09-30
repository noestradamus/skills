# Operation and experiment contracts

The portable unit is this entire skill directory, including `src`, `uv.lock`, references, examples, tests and experiment scripts. Generated evaluation artifacts remain local and are not distributed in Git. Python 3.12, uv and a CPU are required. Docker is additionally required for generated programs and the Linux validation image. No other skill, agent framework or proprietary API is required.

Optional tensor execution uses explicit CPU/CUDA/MPS devices and population batching in supported profiles. See [accelerator execution](accelerators.md) for the capability matrix, separate CUDA lock, checkpoint semantics and verified hardware scope. The default CPU environment remains unchanged.

## Setup and commands

Run `uv sync --frozen` in the skill directory. `uv.lock` pins transitive dependencies and hashes. NEAT-Python's source declares 2.1.0, which was not available by that version on PyPI during setup; its source archive is pinned to `7d9acae0a1e5d7ed6199ffbd525dd15c5c87a86f`. Do not replace the source pin with an unrelated index release. The default Linux source for torch is the official CPU wheel index. macOS wheels support CPU and available MPS hardware. Experiments create CPU tensors by default; supported torch profiles use the explicitly selected device. CUDA uses the separate environment described in [accelerator execution](accelerators.md).

The `neuroevo` executable and `python -m neuroevolution_lab` expose identical commands:

- `doctor`: imports, exact environment identity, methods and Docker daemon availability.
- `validate SPEC.toml`: schema, supported target/composition, engine construction.
- `run SPEC.toml --out DIR`: execute into a new/empty directory.
- `resume DIR`: restore the exact original specification and local checkpoint.
- `inspect DIR`, `report DIR`, `replay DIR --seed N`: stored status, Markdown/SVG evidence, direct saved-candidate replay.
- `evaluate-heldout DIR --out NEW --seed N --cases K`: frozen LLM-agent inference on fresh generated cases.
- `bridge next DIR`, `bridge submit DIR ID --response FILE --provenance TEXT`: explicit host interaction.

The Python API uses `ExperimentSpec`, `execute`, `resume_run`, `replay_run`, and `Context` from `neuroevolution_lab.config` / `.runtime`. Numerical modules also expose pure evaluators and decoders for independent inspection.

For a local collection of saved runs, inventory executed method profiles and
missing reports with:

```bash
uv run --frozen python scripts/release_audit.py --evidence /absolute/path/to/local/runs
```

The directory must already exist. The script writes coverage and current package
source hashes there, and exits unsuccessfully if a profile lacks a completed run
or required reports are missing. This inventory does not verify algorithm
correctness, provenance or comparative performance.

## Specification

```toml
name = "controller pilot"
method = "ga"
target = "cartpole"
seed = 0
population_size = 16
generations = 8

[parameters]
hidden = 4
episodes = 3
horizon = 200

[budget]
max_evaluations = 512
wall_seconds = 600
workers = 1
max_model_calls = 32
```

`method` selects a documented composition profile, not an arbitrary string of modifiers. The machine-readable target matrix is `src/neuroevolution_lab/compatibility.py`. The module reference defines its parameters and inheritance. Unknown top-level fields are rejected. Method parameters are intentionally extensible; verify against the selected reference before editing them. The scheduler is currently serial; `workers` is an upper bound, not a parallelism claim.

Evaluation fitness is maximized. Results contain fitness, objectives, descriptors, constraints, metrics and `measurement_kind=observed|predicted`. Descriptors characterize behavior; novelty is neighbor distance; neither silently replaces task fitness. Metric fields retain environment interactions, rollout trajectories and training work where applicable.

An engine exports `done`, `step(context)`, `summary()` and `replay(seed)` and is pickleable. Every scored candidate goes through `context.evaluate(genome, callable, label=..., kind=...)`. Its result must be a finite JSON-compatible mapping. `context.record(event)` preserves lineage/learning/transfer evidence. For new compositions, add a registry factory, compatibility entry, independent mechanism tests and a frozen demonstration.

## Persistence, budgets and trust

The journal records dispatch before evaluation and records both failures and results. Evaluation IDs and genome/label digests prevent accidental reuse of mismatched evidence. Complete steps save engine, optimizer, population, archives, applicable learner/buffer and RNG state. If interrupted within a step, resume replays from the last complete step and reuses finished evaluation records. Bridge requests and submitted responses are immutable and content identified. Ancillary events are deduplicated within a restored step.

Local checkpoints contain Python pickle objects and are only for trusted local runs. SHA-256 detects accidental damage; it does not make untrusted pickle safe. JSON genomes and the explicit program sandbox are separate interchange paths.

Wall-clock limits cover active execution, including engine initialization and checkpoint restoration, excluding time paused waiting for the host. Durable status and journal records retain the last observed active elapsed time; resume uses the larger value. Work between the last durable record and a hard process kill cannot be measured retrospectively. Limits are checked at evaluation/step boundaries; an already running bounded numerical evaluation may finish after the wall limit. Program execution and HTTP calls also have individual timeouts. Uncertain remote outcomes are not automatically retried, preventing duplicate charges. Model-call counts include pending/failed dispatched requests. Evaluation counts include surrogate queries and candidate failures; compare true environment interactions separately.

Resume preserves the frozen specification; it does not increase a spent budget. Use a new declared run to change experimental limits. Reports preserve negative and partial results. Replays are separate verification measurements, reported as such rather than charged as additional search evaluations.

## Linux and generated programs

`docker build -t neuroevolution-lab:local .` builds the pinned CPU environment. `docker run --rm --network none neuroevolution-lab:local python -m pytest -q` verifies numerical mechanisms in Linux. The generated-program tests run against the host's Docker daemon separately; do not mount a Docker socket into untrusted candidate containers.

The program image is Python 3.12 slim, pulled explicitly before use. The sandbox records the resolved image ID and runs without network, host mounts, capabilities or credentials, under a non-root user, with a read-only filesystem and limits on memory, CPU, processes and elapsed time. AST validation enforces the experiment grammar, while Docker provides process isolation. Production multi-tenant sandbox hardening is separately scoped.
