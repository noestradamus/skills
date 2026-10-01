# Coevolution, bounded POET, and learned surrogates

Read this when the task depends on collaborators, adversaries, evolving tasks, or
an imperfect model that makes evaluations cheaper. These implementations evolve
actual neural weights. Each domain is intentionally small enough for deterministic
CPU tests. None establishes a new benchmark, unrestricted open-endedness, or
superiority to a separately budget-matched baseline.

| Method | Target | Search mechanism | Evidence to inspect |
| --- | --- | --- | --- |
| `cooperative` | `cooperative-tracking` | Separate populations of neural actuator controllers; shared team rewards over multiple collaborators | `cooperative_credit`, partner fitness spread, assembled team score |
| `competitive` | `competitive-rps` | Neural mixed strategies coevolve against current and historical opponents | Relative payoff, fixed-panel mean/worst payoff, cross-play, cycling warning |
| `poet` | `terrain-tracking` | Bounded environment-agent population; task mutation, minimal criteria, novelty, ES optimization, direct and adapted transfers | Environment ancestry, filter decisions, transfer scores and distances, active pair scores |
| `surrogate` | `surrogate-control` | Evolve neural prescriptions against a learned context/action reward predictor; confirm selected policies in the real synthetic domain | Prediction versus true fitness, prediction error before refit, separate evaluation counts |

## Cooperative controller teams

Two heterogeneous neural controllers apply forces to the same damped mass. Each
network observes tracking error, mass velocity, its teammate's previous action,
role, and target phase. A force changes the state both controllers subsequently
observe. The team reward is `1 - tracking_MSE - 0.02 * mean_action_squared`.
Changing one collaborator while holding the focal controller fixed changes its
shared reward.

Each role has its own subpopulation. A candidate is evaluated with the previous
role representative and sampled members of the other subpopulation, using the
same partner panel for all candidates in that role. Its credit is the mean of
those complete-team rewards. Both populations undergo elite-preserving Gaussian
mutation. The newly assembled representative team is measured separately;
individual average credits are not assumed to equal its fitness. The saved
artifact is the best measured complete team.

This implements team-level shared-fitness coevolution, not an ESP neuron encoding,
SANE blueprints, difference rewards, or the book's predator-prey demonstration.
The relevant principles are the book's Chapter 7, printed pages 183–195.

## Competitive neural game agents

The repeated rock-paper-scissors game provides an explicitly nontransitive
competition. A neural agent maps its own and its opponent's previous mixed action
probabilities to its next action probabilities. Both agents respond every round;
fitness is the mean expected zero-sum payoff over 24 rounds. Expected payoffs keep
evaluation deterministic while retaining agent interaction and cycling risk.

Every generation uses a frozen panel of current policies plus a bounded hall of
previous champions. A separate, unchanged nine-network validation panel includes
three near-pure strategies and six independently seeded networks. Validation
tracks both mean and worst payoff. The reported best checkpoint maximizes worst
payoff against that panel; reproduction uses relative training payoff.

A relative gain accompanied by fixed-panel worst-score regression emits a
`cycling_warning`. It is a diagnostic, not proof of a full cycle or evidence of
global progress. Inspect the complete validation vector, behavior distribution,
and cross-play with the previous champion. The fixed panel is a finite reference,
not a guarantee against all possible opponents. The book discusses relative
fitness, historical opponents, and independent progress checks on pages 192–195.

## Bounded POET-style environment-agent coevolution

The `terrain-tracking` domain is a smooth target course for a damped mass, with
four evolving parameters: target amplitude, target frequency, constant wind, and
drag. It does **not** simulate legged locomotion, physical obstacle terrain, or
BipedalWalker. An agent is a 5-input, 4-hidden-unit tanh controller that observes
tracking error, velocity, target velocity, wind, and a constant input.

The implemented loop is:

1. Optimize each paired controller with an antithetic evolution-strategy step.
   Evaluate perturbations and the gradient proposal in the paired environment;
   retain the best confirmed improvement, including the incumbent.
2. Mutate eligible parents' normalized environment parameters. Reject children
   outside `minimal_fitness < score < maximal_fitness` or within the novelty
   threshold of any previously admitted environment. Novelty is Euclidean
   parameter distance, not a behavioral embedding. Admit novel children in
   novelty order, inherit the parent's actual weights, and retain ancestry.
3. For every ordered pair of active environments, evaluate the source controller
   directly in the target and perform a fresh ES adaptation there starting from
   those source weights. Replace the incumbent only if direct or adapted
   transfer improves its measured score. The trace records both attempts even
   when neither succeeds. Sources are frozen before the transfer sweep.
4. Retire the oldest active pair when the bounded capacity is exceeded. Its
   environment remains in the novelty archive and ancestry history.

This retains the coupling of problem generation, policy optimization, and
cross-task transfer described by [Wang et al. (2019)](https://arxiv.org/abs/1901.01753)
and the book's pages 252–257. It is a bounded mechanistic implementation, not a
reproduction of the paper's locomotion results or enhanced POET/PATA-EC. Maximum
raw reward across different tasks does not measure task difficulty or curriculum
progress; inspect pair histories and environment parameters together.

Useful controls: `max_pairs`, `environment_interval`, `transfer_interval`,
`environment_sigma`, `novelty_threshold`, `minimal_fitness`, `maximal_fitness`,
`reproduction_threshold`, and `es_learning_rate`. Each direct/adapted transfer
consumes evaluations, so a larger pair population has quadratic transfer cost.

## Surrogate-assisted neural prescription

The synthetic domain maps context `c` and action `a` to the true reward
`1 - (a - (0.6*sin(pi*c) + 0.2*c))**2 - 0.03*a**2`. A neural prescription maps
context to action. The reward predictor takes context and action as input; it has
20 fixed random tanh hidden features and a ridge-trained output layer. It is a
learned neural model with finite data and capacity, not a disguised call to the
true reward function during prediction.

The initial observations are measured random context/action outcomes. Each
generation evaluates candidate prescriptions using the predictor, selects the
configured number of predicted leaders plus one exploration candidate, and
measures those policies on 33 fixed contexts in the true domain. New outcomes
refit the predictor. Confirmation errors are computed **before** refitting. Every
saved best policy must have a true measurement; an optimistic prediction alone
can never become the reported champion. This implements the predictor/prescriptor
cycle in the book's pages 162–164 without claiming its reported empirical gains.

The journal marks surrogate evaluations as `kind="predicted"`. Summary counts
distinguish predicted controller evaluations, true controller evaluations, and
individual true context/action queries. The common runner's evaluation budget
counts journaled evaluations of both kinds, so it is not itself a count of
expensive true-environment outcomes. `true_confirmations` excludes the additional
exploration policy. The defaults are two predicted leaders and one exploration
policy per generation.

## Reproducibility and interpretation

The examples `cooperative.toml`, `competitive.toml`, `poet.toml`, and
`surrogate.toml` set finite CPU budgets. All search-time candidate evaluations go
through the journaled context. Full engine state includes populations, archives,
predictor weights/data, and a local NumPy RNG; checkpoint/resume tests compare
the complete evaluation stream and final summary.

Saved-best replay performs a fresh environment measurement. For tracking domains,
a different replay seed changes the initial target phases; report it separately
from same-seed reproduction. Competition and prescription use an unchanged
deterministic validation panel/grid, so their replay seed has no effect. Neither
is an independent randomized generalization test.

For conclusions beyond mechanism validation, add multiple search seeds, matched
evaluation budgets, and separate held-out tasks or opponents. Report unsuccessful
transfers, environment rejections, surrogate overestimation, and absolute
regressions along with improvements.

## Five-seed comparison protocol

The following are executable baselines in the same engine and domain, not
placeholders:

| Full method | Baseline setting | Interpretation |
| --- | --- | --- |
| Cooperative shared-credit search | `team_mode = "joint"` | Ordinary evolution of complete two-controller team genomes |
| Competitive search with historical opponents | `archive_size = 0` | Current-opponent-only evolution, same absolute validation panel |
| POET with both transfers | `transfer_mode = "none"` | Environment-agent coevolution without transfer |
| POET with both transfers | `transfer_mode = "direct"` | Direct-only transfer, isolating adaptation cost and benefit |
| Surrogate-assisted prescription | `search_mode = "direct"` | True-domain evolutionary evaluation of every neural candidate |

Use seeds `0, 1, 2, 3, 4`. Hold controller architecture, initial population,
mutation scale, domain, and validation conditions fixed. Each example has a
matching `*-baseline.toml`; `poet-direct-baseline.toml` is the second POET ablation.
Search traces, checkpoints, and replay outputs remain separate per seed and
condition. Run this Python block from the package directory with its `.venv`
interpreter to instantiate the matrix:

```python
from pathlib import Path
from neuroevolution_lab.config import load_spec
from neuroevolution_lab.runtime import execute, replay_run

for seed in range(5):
    for name in ("cooperative", "cooperative-baseline",
                 "competitive", "competitive-baseline",
                 "poet", "poet-baseline", "poet-direct-baseline",
                 "surrogate", "surrogate-baseline"):
        spec = load_spec(f"examples/{name}.toml")
        spec.seed = seed
        # Same total journal budget; long horizon lets the budget stop each run.
        spec.generations = 1000
        spec.budget.max_evaluations = 500
        spec.budget.wall_seconds = 180
        path = Path("runs/ecology-comparison") / name / f"seed-{seed}"
        result = execute(spec, path)
        if result["summary"]["generation"]:
            replay_run(path, seed=10000)
```

Re-use a finished run with replay; use the shared runner's resume operation for
an interrupted run with the original spec. Do not overwrite a nonempty run
directory. `budget_exhausted` is expected in this protocol. Compare only completed
generation checkpoints; a partially evaluated next generation is journaled but
not selected into the checkpoint. Report those unused evaluations explicitly.

For cooperation and competition, compare saved-best replay outcomes at common
journal evaluation cutoffs, and report per-seed values plus median and range.
Competition also reports `game_matches` and `game_rounds`: an evaluation against
a larger opponent panel costs more game simulation, even if journal counts match.
For POET, report admitted and active environment descriptors, pair rewards,
admissibility rejections, and transfer acceptance rate. Different arms generate
different environments; their maximum raw rewards are not comparable measures
of task difficulty. A performance claim needs a predeclared common held-out
environment panel with every condition evaluated on that same panel.

For surrogates, also compare true reward against cumulative `true_outcome_queries`
at common query cutoffs, including bootstrap data. Generation counts and total
journal evaluations are not substitutes for expensive sample counts. Report
pre-refit prediction MAE and full true/predicted query counts. Five seeds provide
a small reproducibility check; they do not establish statistical superiority.

Generate the nine-condition, five-seed acceptance matrix with
[the ecology protocol](../scripts/ecology_acceptance.py):

```bash
uv run --frozen python scripts/ecology_acceptance.py --output runs/ecology-acceptance
```

The output directory must not exist. The script freezes specifications and source
hashes, retains every raw run with a compressed journal, and records common
held-out evaluations. Outputs stay local; historical runs are not bundled.
