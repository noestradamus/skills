# Search engines and measured controller tasks

All methods maximize measured fitness, journal each candidate through the shared
runtime, and serialize their complete optimizer and random-generator state.
They are small CPU reference implementations; completing an example does not
establish superiority over another optimizer.

| Method ID | Actual mechanism | Evidence to inspect |
|---|---|---|
| `fixed_controller` | Exactly one seeded initial MLP, one measured evaluation, no optimization | Unchanged saved weights and inference replay |
| `random_search` | Independent fresh Gaussian weight samples, no evolutionary selection | Baseline candidate count and measured results |
| `ga` | Truncation selection, uniform crossover, independent Gaussian weight mutation, one elite | Parent IDs, measured fitness, decoded MLP weights |
| `es` | Antithetic Gaussian parameter perturbations and a fitness-standardized finite-difference update of the distribution mean | Paired perturbations, estimator norm, evaluated offspring |
| `cma_es` | pycma ask/tell covariance-matrix adaptation | Measured fitness, population, evolving step size; full optimizer in checkpoint |
| `nsga2` | pymoo NSGA-II nondominated sorting, crowding, crossover and mutation | Nondominated quality/negative-weight-energy objective pairs |
| `novelty` | k-nearest-neighbor distance in measured behavior space guides reproduction | Behavior descriptors, novelty scores, bounded historical archive |
| `nslc` | Novelty and fraction of behavioral neighbors beaten on task fitness are separate Pareto objectives | Novelty/local-competition vectors and nondominated selection |
| `map_elites` | pyribs grid archive; offspring mutate stored elites and replace incumbents only under archive rules | Insertion statuses, archive-parent IDs, coverage and QD score |

The ES estimator changes neural weights directly; it does not backpropagate
through the task. CMA-ES uses a full covariance matrix and is intended here for
small controllers. NSGA-II's second objective is negative mean-square weight
magnitude, **not** architecture size. NSLC uses current population plus archived
behaviors for neighbor comparisons. The novelty archive admits candidates above
a fixed threshold and retains the newest `archive_capacity` admissions. These
choices are recorded algorithm variants, not exact reproductions of every paper.

The novelty and NSLC archive retains genotypes as well as measured behaviors and
fitness. Each non-elite offspring parent comes from that archive with probability
`archive_parent_probability` (default .25); otherwise it comes from the selected
current population. Archived parents have stable generation/index/content-hash
IDs in lineage records. This explicit **reproductive-archive variant** goes beyond
the behavioral scoring memory of basic novelty search; setting the probability
to zero recovers population-only reproduction. A regression test replaces the
entire current population and verifies that an older retained genotype still
produces actual offspring. Archive truncation removes reproductive eligibility
for entries beyond the declared capacity.

## Genotypes and evaluators

`direct_mlp` is a flattened two-layer neural network. The first layer has `hidden`
tanh neurons; each layer includes a bias. XOR uses a sigmoid output, other tasks
use tanh. No language model scores these environments.

- `xor`: all four binary inputs; fitness is one minus squared prediction error.
  Its two descriptors are the predictions for inputs (0,1) and (1,0). This is a
  four-case mechanism test, not evidence of generalization.
- `cartpole`: the standard cart-and-pole equations with Euler integration at
  0.02 seconds, force +/-10, failure at 2.4 units or 12 degrees. Fitness is mean
  survival time from seeded initial states. Descriptors are episode-average cart
  position and pole angle. This local reference is not a claimed Gymnasium
  benchmark reproduction; compare identical local physics and episode budgets.
- `navigation` (aliases `deceptive_navigation`, `deceptive_maze`): a continuous
  point controller must move around a vertical wall, with an opening above y=.8.
  Fitness is negative final goal distance, and final x/y are measured descriptors.
  Every rollout records its trajectory and wall collisions. The straight path
  yields deceptive local progress but cannot cross the wall.

MAP-Elites uses [0,1]^2 descriptor ranges for XOR/navigation and physical
CartPole bounds for its two measures. Novelty distances use raw descriptor
coordinates: use navigation for the default novelty demonstrations; explicitly
review scaling before comparing unlike physical measures.

## Bounded acceptance

Run the examples through the shared CLI, inspect actual evaluations and replay
the saved best controller. Multi-seed matched-budget experiments, unseen initial
conditions and random-search/gradient baselines are needed for empirical benefit
claims. The bundled tests check a hand-constructed XOR solution, a maze collision
and detour, nearest-neighbor scores, Pareto non-domination, antithetic pairing,
archive-parent reproduction, and identical continuation after pickling.

`examples/compare-search.py OUTPUT_DIRECTORY` first writes its frozen protocol,
then runs random search, GA, ES and CMA-ES on the same CartPole topology and
evaluation budgets for seeds 0 through 4. It evaluates the selected policies on
five disjoint sets of unseen initial conditions and preserves every seed. The
output directory must be new. The shipped sampling/update scales are explicit
method settings, not a claim of equally optimized hyperparameters.
Adding `--navigation` selects a separate frozen five-seed protocol comparing
objective-only GA with novelty search, NSLC and MAP-Elites on deceptive navigation.
It records raw held-out successes as well as distances and archive coverage.
`--fixed` selects a separate five-seed non-optimizing controller baseline; each
seed evaluates one initial network. It is distinct from best-of-many random
search. Fixed-baseline runs are not described as using the full search budget.

## Primary references and implementations

- [CMA-ES/pycma](https://github.com/CMA-ES/pycma)
- [pymoo NSGA-II](https://pymoo.org/algorithms/moo/nsga2.html)
- [pyribs novelty-search example](https://docs.pyribs.org/en/stable/tutorials/ns_maze.html)
- [pyribs GridArchive](https://docs.pyribs.org/en/stable/api/ribs.archives.GridArchive.html)
- [Novelty search, Lehman and Stanley](https://doi.org/10.1162/EVCO_a_00025)
- [Novelty search with local competition, Lehman and Stanley](https://doi.org/10.1145/2001576.2001607)
- [MAP-Elites, Mouret and Clune](https://arxiv.org/abs/1504.04909)
- [Evolution strategies for reinforcement learning, Salimans et al.](https://arxiv.org/abs/1703.03864)
