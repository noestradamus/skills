# Structural neural evolution

## NEAT backend and fidelity

`neat` evolves real neural connection genes and neuron genes. The adapter uses
NEAT-Python at immutable source commit
`7d9acae0a1e5d7ed6199ffbd525dd15c5c87a86f`; its upstream version label is not a
claim that the same version is published on PyPI. Connections retain innovation
numbers, crossover aligns those markings, and species protect distinct structures.

The generated configuration is saved in the result. It starts without hidden
nodes, enables node/connection additions, disables deletion, uses canonical
fitness sharing, proportional spawn allocation, a dynamic compatibility
threshold, interspecies crossover, connection-only compatibility distance and
the paper's 75-percent disable interpretation. The upstream `disable_rule`
setting names this last interpretation `neat-python`; its alternative `stanley`
matches the original C++ inheritance behavior and has different probabilities.

Bias genes, feed-forward networks, task-specific fitness, population size and
mutation rates remain documented experimental choices. This is not advertised as
an exact replication of the 2002 benchmark. Python's global random state is
temporarily replaced with the engine's private saved state and restored even on
interruption. Population/species/innovation state is retained in the checkpoint.

## Corrected canonical profile

New runs use `evolution_profile="paper-profile-v2"`. A local `CanonicalGenome`
adapter corrects two departures in the pinned backend: the weight term in the
book's equation 3.1 is averaged over matching connection genes, and equal-fitness
parents can both contribute disjoint/excess genes. For ties, each unmatched gene
has a half chance of inheritance; cycle and endpoint-conflict checks preserve a
valid feed-forward graph. Unequal-fitness crossover remains upstream behavior.
The structural normalization N is the larger connection count, including disabled
genes; the optional small-genome N=1 convention is not selected. Node attributes
and enabled-state differences are excluded from compatibility distance.

Independent fixtures cover the equation, unequal topology, disabled genes,
tied-parent inheritance, DAG validity and unchanged unequal-fitness behavior.
Existing checkpoints with the upstream genome type retain `evolution_profile="legacy"`.
Their historical searches are not evidence for the corrected profile. See
[the mechanism tests](../tests/test_structural.py) and run
[the structural demonstration protocol](../scripts/review_structural_acceptance.py)
to produce results for the current implementation.

## CPPN and HyperNEAT

`cppn` evolves heterogeneous activation functions (`tanh`, sine, Gaussian,
identity, sigmoid) in a NEAT graph. Four inputs x/y/radius/constant generate an
intensity at each coordinate. The reference target is a concentric radial pattern;
fitness uses the full generated image, which is included in the measured result.

`hyperneat` evolves a five-input CPPN that generates the actual controller weights.
Its query is source x/y, destination x/y, and their Euclidean distance. Inputs,
hidden neurons, and output neurons occupy normalized coordinate rows at y=-1,0,1.
Within each row x ranges from -1 to 1; a singleton sits at x=0. A distinct bias
coordinate is appended for each source layer. Only adjacent layers connect.

The expression value is `tanh(CPPN(query))`. Magnitudes at or below the configured
threshold express no connection; larger values are rescaled from the threshold
to one and multiplied by `weight_scale`, preserving sign. Decoder tests compare
every output to a hand-calculated constant CPPN and decode the same CPPN at two
hidden-layer resolutions. This verifies the representation and decoding, not
automatic successful transfer across resolutions.

The phenotype has tanh hidden activations, sigmoid outputs for XOR and tanh
outputs for control. These conventions are explicit choices. This is
**fixed-substrate HyperNEAT**; it does not implement ES-HyperNEAT's adaptive
substrate discovery. The independent decoder introduces no TensorNEAT/GPL/JAX
runtime dependency.

## Pinned upstream interspecies repair

The pinned NEAT-Python `DefaultReproduction.reproduce` clears each species'
parent members before all later species finish interspecies mating. With two
species and interspecies crossover enabled, a later species can sample an empty
earlier species and raise `IndexError`. `CanonicalReproduction` is a narrow local
adapter: it defers only those member clears until reproduction returns, then
restores the original Species objects. It does not patch global library state.

Regression tests reproduce the pinned upstream failure and verify that the local
adapter completes cross-species mating. A differential test disables
interspecies mating and verifies identical offspring genes and final RNG state
against the unchanged upstream implementation. Separate tests check innovation
alignment despite reversed gene order, fitter-parent disjoint inheritance, the
fresh 75-percent disable draw, species partitioning, mean fitness sharing and
proportional allocation versus the normalized alternative. Source-level repair
is recorded; this is not represented as an unmodified upstream implementation.

## Modular NAS

`modular_nas` evolves one to three trainable hidden-layer modules. Each module
has width 2,4,8 and tanh or ReLU activation. Mutations change width/activation or
add/remove modules. Each candidate is initialized afresh and really trained using
PyTorch Adam on seeded continuous-XOR examples. Selection uses held-out validation
loss. Initial/final training loss, validation loss/accuracy, parameter count and
trained tensors are recorded. A distinct final test split is required when
reporting generalization because the validation split participates in search.
Replay loads the saved trained tensors and performs inference on the requested
seed's inputs. It never retrains the architecture. The returned training-loss
metadata describes the original training run, while validation metrics are
remeasured on the replay inputs.

This is architecture evolution with gradient-trained candidates. It does not
claim network morphism, weight inheritance, full framework-level NAS, or a win
over gradient-only training. The tiny network family is deliberate CPU acceptance
scope. Repeated-seed trials should include matched training-step and wall-time
budgets, not merely equal numbers of architectures.

## Primary references

- [NEAT, Stanley and Miikkulainen](https://doi.org/10.1162/106365602320169811)
- [Pinned NEAT-Python source](https://github.com/CodeReclaimers/neat-python/tree/7d9acae0a1e5d7ed6199ffbd525dd15c5c87a86f)
- [CPPNs, Stanley](https://doi.org/10.1007/s10710-007-9028-8)
- [HyperNEAT, Stanley, D'Ambrosio and Gauci](https://doi.org/10.1162/artl.2009.15.2.15202)
- [Regularized architecture evolution, Real et al.](https://arxiv.org/abs/1802.01548)

The NAS reference motivates architecture search; this bounded adapter uses
elitist selection and does not claim to reproduce regularized aging evolution.
