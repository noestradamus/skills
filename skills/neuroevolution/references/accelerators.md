# Devices, batching and accelerator evidence

The default remains the reproducible CPU reference backend. Select the tensor
backend explicitly when using a GPU or comparing population batching on CPU:

```toml
[compute]
backend = "torch"
device = "mps"  # "cpu", "cuda", or "cuda:0" are also recognized
batch_size = 32
```

`validate` and `doctor` check what the current process can access. An unavailable
device is an error, never an automatic CPU fallback. MPS experiments reject
`PYTORCH_ENABLE_MPS_FALLBACK=1` so unsupported operations cannot masquerade as GPU
measurements. Some restricted execution environments cannot access Metal even
when the host Mac has a supported GPU; run through a host execution environment
with GPU access. Do not interpret a restricted-process availability result as a
hardware inventory.

## What moves to the device

| Profiles | Tensor execution | CPU work and boundaries |
| --- | --- | --- |
| Fixed controllers, random search, GA, ES, CMA-ES, NSGA-II, novelty, NSLC, MAP-Elites | Fixed-network population and environment axes run together for XOR, CartPole and navigation | Variation, optimizer state, archives and seeded initial-condition construction remain on CPU |
| NEAT, CPPN, HyperNEAT | Heterogeneous feed-forward phenotypes group nodes by depth/function; coordinate queries and generated controller rollouts are batched | Canonical NEAT-Python innovation, crossover, speciation and reproduction remain unchanged; graph compilation is CPU work |
| Gradient refinement and evolved initializations | Independent SGD for every candidate runs as a population tensor; tasks remain distinct | Selection, inherited genotype arrays and immutable result records return to CPU |
| Model merging, adapter/full-parameter evolution | Aligned model tensors and GRU population forward passes execute on the device; actual source-model training uses that device | Shared input sequences; recurrent time axis remains sequential; this remains the small autoregressive model profile |
| ERL | Actor/critic tensors, optimizer state and gradient minibatches use the device | Candidate rollouts and the reference tracking environment remain sequential; this is not a fully device-resident simulator |
| Plasticity and DQD | Actual synaptic updates or objective/descriptor Jacobians execute on the device | Candidate evaluation remains sequential; MPS DQD uses float32 instead of the CPU/CUDA float64 Jacobian profile |
| Modular NAS | Each architecture's training and saved-tensor inference use the device | Architectures are trained sequentially; heterogeneous architecture training is not population-batched |
| Ecology and LLM-agent profiles | No local tensor backend selected through this option | Ecology remains CPU reference. A local/hosted LLM endpoint controls its own inference hardware independently |

The accelerated NEAT evaluator is an additional **phenotype evaluation backend**
for the same canonical evolution implementation. It is not TensorNEAT or a new
NEAT variant. All 18 built-in activations and seven aggregations are matched to
upstream scalar fixtures. Recurrent phenotypes and custom/overridden functions
are explicitly unsupported. HyperNEAT keeps the existing fixed substrate.

CPU controller/structural tensor evaluation uses float64; CUDA/MPS use float32.
Training kernels use float32. Independent executions and different batch shapes
can differ numerically; thresholds and close fitness ties can amplify differences
into different evolutionary trajectories. Tests use declared numerical tolerances
and check checkpoint persistence separately from independent-run agreement.

## Installation

CPU and Apple MPS use the root locked environment:

If a restricted host cannot access uv's cache, configure a writable `UV_CACHE_DIR`.
For an already initialized environment, `.venv/bin/python -m neuroevolution_lab`
is also equivalent to `uv run --frozen neuroevo`; it uses the installed environment
directly. CUDA's corresponding interpreter is `environments/cuda/.venv/bin/python`.

```bash
uv sync --frozen
uv run --frozen neuroevo doctor
uv run --frozen neuroevo validate examples/accelerators/gradient-mps.toml
uv run --frozen neuroevo run examples/accelerators/gradient-mps.toml --out runs/gradient-mps
```

Linux x86-64 CUDA has a separate exact environment, preserving the portable CPU
lock. It selects PyTorch 2.14.0+cu130 from the official CUDA 13.0 index; an NVIDIA
GPU and compatible driver are required. From the skill directory:

```bash
uv sync --project environments/cuda --frozen
uv run --project environments/cuda --frozen neuroevo doctor
uv run --project environments/cuda --frozen neuroevo run examples/accelerators/gradient-cuda.toml --out runs/gradient-cuda
```

Use that environment consistently for validate/run/resume/replay. A later root
`uv run` uses the root CPU environment, not the CUDA environment. CUDA package
resolution and a Linux installation dry-run do not establish driver, hardware,
kernel or performance compatibility. Native macOS ARM64 CPU and Apple M2 MPS
execution have been exercised across the 20 supported profiles, with saved-candidate
replay. NVIDIA hardware execution remains unverified. Repeat device checks with
[the accelerator tests](../tests/test_accelerator_runtime.py) and generate local
operation results with:

```bash
uv run --frozen python scripts/accelerator_acceptance.py --out runs/device-check --devices cpu mps
```

Choose only devices available to the current process; use the CUDA environment
when checking an NVIDIA GPU. These small operation examples do not establish a
performance advantage.

## Budgets, checkpoints and measurement

`batch_size` is a numerical batch limit, not a CPU worker count. One orchestration
process continues to own evidence and selection. Each candidate is journaled and
charged before its batch callback runs. Partially cached batches evaluate only
missing candidates. If the remaining budget cannot fund a complete batch, the
affordable candidates are committed before budget exhaustion is reported. Failed
batch kernels charge every dispatched candidate.

Checkpoints preserve active accelerator RNG state as well as CPU RNG, model and
optimizer state. Resume validates device availability and preserves the original
compute configuration. Automatic checkpoint migration between devices is not
implemented. Historical CPU checkpoints retain CPU reference defaults.

GPU timing synchronizes the selected device. Batch time is shared across
candidates; per-candidate seconds is an amortized allocation, not independent
latency. CUDA exposes the process allocator's peak since its last reset, explicitly
labelled so it is not mistaken for an isolated per-run peak. MPS records current/driver allocations but
does not claim a measured peak. Reports include the actual device, backend and
batch records. Source-model preparation and reports still contribute to total
experiment wall time.

The five-seed benchmark measures a declared dense inner-learning kernel,
including transfers and measurement extraction. It compares scalar CPU,
population-batched CPU and population-batched GPU. This separates batching gains
from accelerator gains. It does not establish whole-experiment speedups for every
method or improved discovery quality. Small workloads may be slower on a GPU.
Generate measurements for your own hardware with
[the benchmark script](../scripts/benchmark_accelerators.py):

```bash
uv run --frozen python scripts/benchmark_accelerators.py --out runs/device-benchmark --devices cpu mps
```

Primary implementation references: [PyTorch CUDA](https://docs.pytorch.org/docs/stable/notes/cuda.html),
[PyTorch MPS](https://docs.pytorch.org/docs/2.14/notes/mps.html), and
[uv's PyTorch configuration](https://docs.astral.sh/uv/guides/integration/pytorch/).
