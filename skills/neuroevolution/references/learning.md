# Learning, differentiable QD, and actual language-model tensor evolution

These are executable PyTorch experiments on deliberately small domains, with CPU reference execution by default and optional [device-aware tensor execution](accelerators.md). They establish mechanism support and bounded measurements. They do not reproduce a large-model, robotics, or state-of-the-art result from the book. An agent can inspect the journal and replay a checkpoint; a prompt is never labelled a model-weight mutation.

## Contracts and implemented methods

| Method / target | Actual search object and mechanism | Meaning of replay |
|---|---|---|
| `gradient_refinement` / `sine_regression` | A direct-encoded one-hidden-layer tanh network. Candidate-specific SGD fits support points; independent validation points determine selection. `none` skips SGD. Baldwinian mode selects learned performance but reproduces original genes. Lamarckian mode transmits learned weights. | Evaluate the **saved selected phenotype**, with no fresh training, on new input points. |
| `evolutionary_initialization` / `sine_task_family` | A shared neural initialization. Each training task independently starts from that initialization, adapts on support points, and receives query-set loss. Selection averages across training tasks. Offspring inherit the initialization. Lamarckian mode is rejected because it would ambiguously collapse task-specific acquired weights. | **Fresh, explicitly counted adaptation** from the selected initialization on six unseen sine tasks. This is not frozen-controller inference. |
| `evolved_plasticity` / `associative_memory` | Initial synapses; separate synapse-specific A, B, C, D coefficients; synapse-specific learning rates; and a learned neuromodulator. Every episode starts from genotype weights. The rule is `Δw = η m (A pre post + B pre + C post + D)`. | Run fresh episode seeds using the saved rule genotype; plastic weights evolve during each lifetime and are reset between episodes. With three binary cues, association mappings can overlap training; no disjoint-association claim. |
| `erl` / `tracking_control` | A population of neural policies generates trajectories into a shared replay buffer. An additional noisy RL actor contributes experience. A DDPG actor/critic performs gradient updates with target networks; the actor is inserted into the next evolutionary population. | Frozen selected policy on eight new environment rollouts; no gradient updates. |
| `differentiable_qd` / `differentiable_arm` | Four-joint arm angles; analytic Torch-autograd Jacobians for objective and two endpoint descriptors. A weighted combination of normalized gradients proposes candidates, which compete within explicit MAP-Elites cells. | Recompute every archived cell/score and the selected arm. This deterministic audit is not a held-out environment benchmark. |
| `model_merging` / `tiny_autoregressive` | Train two embedding–GRU–linear autoregressive LMs from one common initialization, each on a different arithmetic task family. Evolve three convex coefficients for embedding/recurrent/output groups. Merge actual corresponding tensors, then evaluate next-token loss. | Frozen selected merged tensors on a predeclared, disjoint test task partition. |
| `parameter_evolution` / `tiny_autoregressive` | Train a local base LM on both arithmetic domains. Evolve either an actual low-rank output-projection update `BA/rank` with frozen base tensors (`mode="adapter"`) or the full neural parameter vector (`mode="full"`). | Frozen selected effective tensors on the disjoint test partition. |

The model target uses 12 tokens: ten digits and two operation markers. Each sequence identifies a start value and stride, then follows modular addition or subtraction. The 80 distinct `(operation,start,stride)` tasks are split into 48 training, 16 validation and 16 test tasks **before** constructing sequences. There are no repeated task identifiers across splits. Validation determines evolutionary selection; test loss never enters selection. Teacher-forced next-token loss includes all prediction positions, including the non-predictable start/stride positions; metrics therefore should not be interpreted as a universal reasoning score.

## Faithfulness and explicit departures

Book references use printed pages: gradient/evolution hybrids pp. 318–326; evolving local learning rules and neuromodulation pp. 326–335; differentiable QD p. 130; evolutionary model merging pp. 353–356; parameter search pp. 356–359.

The inheritance distinction is literal, with hashes for pre-learning, acquired, and transmitted weights. The initialization engine retains distinct adapted hashes for every training task. Selection operates on post-adaptation performance, not a proxy for whether a learning rate changed.

Plasticity is an associative-memory demonstration, not the book's physical robot. During support, observed targets clamp postsynaptic activity. During query, the network uses its own predicted activity with the feedback-available signal set to zero. A sigmoid neuromodulator receives cue activity, postsynaptic activity and that signal. The evolving ABCD rule, rate and modulator determine updates at each step. Rates are bounded and synapses clipped. A frozen-synapse counterfactual is measured on the same episodes. This support protocol and teacher clamping are disclosed rather than described as reward-only learning.

ERL implements the substantive coupled-population mechanism with deterministic small continuous control and a DDPG inner learner. It is not a numerical reproduction of the original benchmark. Trajectories are stored in evaluation evidence and appended to engine state **after** `ctx.evaluate` returns: journal-cache replay can reconstruct the shared replay buffer when a partially completed generation is resumed.

ERL also has explicit `parameters.mode="evolution_only"` and `"learning_only"` controls. Evolution-only runs policy rollouts and genetic reproduction with zero gradient updates and no RL actor trajectories. Learning-only uses only noisy DDPG actor trajectories and returns the final trained actor, without population selection, crossover, mutation, or reinsertion. It does not attach a pre-update measured training score to that final unmeasured actor. The normal `hybrid` mode selects its best observed population policy. These selection differences are disclosed in the comparison protocol.

The DQD implementation is named **normalized-gradient MAP-Elites variant**. It does **not** implement the CMA-MEGA/CMA-MAEGA adaptive coefficient emitter, and its summary says so. It computes true objective and descriptor Jacobians, normalizes each row, draws descriptor coefficients, takes an objective-ascent/descriptor-exploration step, and applies archive replacement. Twenty percent of proposals are random restarts. `gradient_proposals=false` is an explicit random-proposal archive control, not a differentiable optimizer. No claim of canonical CMA-MEGA implementation or benchmark reproduction is made.

Tensor merging verifies names, shapes, dtypes and finite values; both source models share their starting checkpoint. There is no learned permutation matching, no claim that arbitrary independently trained models are semantically aligned, and no external model download. Tiny-model parameter evolution does not alter the host assistant or any hosted model. Both default adapter mode and full-parameter mode are real tensor searches.

## Examples, controls and costs

The corresponding TOML files in `examples/` freeze three generations with small populations. Additional files demonstrate Lamarckian refinement and full-parameter LM evolution. `*-baseline.toml` files define the following controls:

| Family | Control | Cost interpretation |
|---|---|---|
| Refinement | No inner gradient learning | Equal candidate evaluations; different gradient compute, explicitly counted. |
| Initialization | Random parent selection | Same population, generations, adaptation and query budgets. |
| Plasticity | Disabled lifetime updates | Same episodes and genes; acquired synaptic change is exactly zero. |
| ERL | No learned-actor reinsertion | Same trajectories and gradient updates; one coupling mechanism is removed. |
| DQD | Uniform random arm proposals | Same candidate evaluations; Jacobian costs differ. Report coverage and objective separately. |
| Merging / parameter evolution | Random parent selection | Same model training, candidate evaluations and validation data. This is a neutral-selection control, not exhaustive or independent random search. |

The random-parent control still records the best observed candidate for final reporting. It does not use fitness to choose reproductive parents. These controls isolate specified mechanisms; they do not prove that the full method is optimal against every alternative.

Run the frozen five-seed suite with:

```bash
.venv/bin/python examples/learning_acceptance.py --output runs/learning-acceptance
```

The output directory must not exist. The script writes `protocol.json` before execution, containing exact specifications, config hashes, seeds and evaluation rules. It retains each run's manifest, journal, checkpoint and replay result and writes machine-readable `results.json` / `summary.json`. It reports all paired outcomes, including losses. Five seeds on these small domains establish a bounded observation, not statistical significance or broad superiority. Do not tune on this test set and then present it as untouched.

Summaries expose gradient updates, environment interactions, plastic updates, tensor training steps or proposal Jacobian counts as applicable. Candidate evaluation counts alone are not a claim of equal total compute. Language-model training is a one-time operation in the first generation and is journaled; subsequent candidates reuse trained sources/base. Checkpoint restoration preserves those actual trained tensors.

ERL's `gradient_updates` counts paired DDPG iterations, with separate `actor_optimizer_steps` and `critic_optimizer_steps` fields. Plasticity's `episode_interactions` includes both learned and frozen-counterfactual rollouts, while `lifetime_updates` counts actual local-update steps only. Frozen-model replay performs no training. Initialization replay reports the new task adaptation cost explicitly.

The requested hybrid-versus-pure-controls comparison is independently frozen and executed with:

```bash
.venv/bin/python examples/erl_controls_acceptance.py --output runs/erl-full-controls
```

It uses five seeds. All three conditions receive 300 training environment interactions: hybrid has four population plus one RL rollout per generation; each pure control has five rollouts. Hybrid and DDPG perform 15 actor and 15 critic updates; evolution performs zero. Each receives 160 further evaluation interactions, which never influence learning or selection. Equal interactions do not imply equal compute. `protocol.json` includes exact specifications and module hashes.

## Meaningful verification

`tests/test_learning.py` checks acquired versus inherited parameters; actual loss-changing gradient updates; disjoint meta-learning tasks; associative learning under an explicit known local rule and its sign reversal; modulation changes; both replay-buffer sources and exact actor reinsertion; replay of cached ERL trajectories; finite-difference agreement for all DQD Jacobian rows; archive consistency; disjoint LM task partitions; merge endpoints and shape rejection; real source-model training; adapter isolation; full-parameter changes; ablation effects; and deterministic checkpoint continuation for every method. A passing test establishes its assertion, not the corresponding paper's reported performance.

Primary sources: [ERL](https://arxiv.org/abs/1805.07917), [Differentiable Quality Diversity](https://arxiv.org/abs/2106.03894), and [Evolutionary Optimization of Model Merging Recipes](https://arxiv.org/abs/2403.13187), alongside the book page ranges above. These define mechanism families; local adaptations are specified in this reference.
