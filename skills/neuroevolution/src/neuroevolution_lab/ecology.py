"""Bounded coevolution and learned-surrogate neural-controller experiments.

These deliberately small domains make the mechanisms auditable on one CPU.
Every search-time environment or predictor evaluation goes through the runner's
context; saved-state replay is a fresh measurement, not a stored fitness value.
"""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np


def network_size(inputs: int, hidden: int = 4, outputs: int = 1) -> int:
    return inputs * hidden + hidden + hidden * outputs + outputs


def neural_action(genome, observation, inputs=5, hidden=4, outputs=1):
    """Decode every genome coordinate into a one-hidden-layer tanh network."""
    g = np.asarray(genome, dtype=float)
    x = np.asarray(observation, dtype=float)
    n = inputs * hidden
    h = np.tanh(x @ g[:n].reshape(inputs, hidden) + g[n : n + hidden])
    k = n + hidden
    y = h @ g[k : k + hidden * outputs].reshape(hidden, outputs) + g[-outputs:]
    return np.tanh(y)


def measurement(fitness, descriptor, **metrics):
    return {
        "fitness": float(fitness),
        "descriptor": [float(x) for x in descriptor],
        "constraints": True,
        "metrics": metrics,
    }


def _breed(population, scores, rng, sigma):
    order = np.argsort(-np.asarray(scores), kind="stable")
    elites = np.asarray(population)[order[: max(2, len(order) // 4)]]
    children = [elites[0].copy()]
    while len(children) < len(population):
        parent = elites[int(rng.integers(len(elites)))]
        children.append(parent + rng.normal(0, sigma, parent.shape))
    return np.asarray(children)


class _Engine:
    def __init__(self, spec):
        self.spec = dict(spec)
        self.params = dict(spec.get("parameters", {}))
        self.seed = int(spec.get("seed", 0))
        self.rng = np.random.default_rng(self.seed)
        self.generation = 0
        self.generations = int(spec.get("generations", 5))
        self.population_size = int(spec.get("population_size", 12))
        self.sigma = float(self.params.get("mutation_sigma", 0.2))
        method = spec.get("method")
        if method in TARGETS and spec.get("target") not in TARGETS[method]:
            raise ValueError(f"{method} supports targets: {', '.join(TARGETS[method])}")
        if self.generations < 1 or self.population_size < 4 or self.sigma <= 0:
            raise ValueError("generations >= 1, population_size >= 4, mutation_sigma > 0 required")
        self.history = []

    @property
    def done(self):
        return self.generation >= self.generations

    def _finish(self, ctx, row):
        self.history.append(row)
        ctx.record(row)
        self.generation += 1


def cooperative_episode(team, *, seed=0, horizon=48):
    """Two distinct actuators control the same damped mass along a target path.

    Both controllers affect every next observation and share the resulting team
    reward. The third observation is the teammate's previous action. Neither
    individual can be assigned a context-free fitness in this domain.
    """
    team = np.asarray(team)
    rng = np.random.default_rng(seed)
    phases = rng.uniform(-np.pi, np.pi, 3)
    errors, energies, actions = [], [], []
    for phase in phases:
        x, v = 0.0, 0.0
        previous = np.zeros(2)
        for step in range(horizon):
            t = step * 0.08
            target = 0.55 * np.sin(t + phase)
            current = np.array([
                float(neural_action(g, [target - x, v, previous[1 - i], 2 * i - 1, np.cos(t + phase)])[0])
                for i, g in enumerate(team)
            ])
            # Both force contributions are indispensable parts of the dynamics.
            v = 0.86 * v + 0.12 * (current[0] + current[1])
            x += 0.08 * v
            errors.append((target - x) ** 2)
            energies.append(float(np.mean(current ** 2)))
            actions.append(current)
            previous = current
    error = float(np.mean(errors))
    effort = float(np.mean(energies))
    return measurement(1 - error - 0.02 * effort, np.mean(actions, axis=0), mse=error, effort=effort)


class CooperativeEngine(_Engine):
    """Heterogeneous team coevolution with shared fitness and sampled partners."""
    def __init__(self, spec):
        super().__init__(spec)
        self.dimension = network_size(5)
        self.populations = self.rng.normal(0, 0.45, (2, self.population_size, self.dimension))
        self.representatives = self.populations[:, 0].copy()
        self.collaborators = int(self.params.get("collaborators", 2))
        self.team_mode = self.params.get("team_mode", "coevolution")
        if self.team_mode not in ("coevolution", "joint"):
            raise ValueError("team_mode must be coevolution or joint")
        if self.collaborators < 2:
            raise ValueError("cooperative requires collaborators >= 2 to expose partner-dependent credit")
        self.best_team = None
        self.best_fitness = None

    def _joint_step(self, ctx):
        """Baseline: each candidate jointly encodes both controllers in a team."""
        teams = self.populations.transpose(1, 0, 2).reshape(self.population_size, -1)
        scores = []
        for index, genome in enumerate(teams):
            team = genome.reshape(2, self.dimension)
            result = ctx.evaluate(genome.tolist(), lambda: cooperative_episode(team, seed=self.seed),
                                  label=f"cooperative/g{self.generation}/joint_team/{index}")
            scores.append(result["fitness"])
            if self.best_fitness is None or result["fitness"] > self.best_fitness:
                self.best_fitness, self.best_team = result["fitness"], team.copy()
        self.representatives = teams[int(np.argmax(scores))].reshape(2, self.dimension).copy()
        teams = _breed(teams, scores, self.rng, self.sigma)
        self.populations = teams.reshape(self.population_size, 2, self.dimension).transpose(1, 0, 2)
        self._finish(ctx, {"event": "cooperative_joint_generation", "generation": self.generation,
                           "team_fitness": float(max(scores)), "best_fitness": self.best_fitness})

    def step(self, ctx):
        if self.done:
            return
        if self.team_mode == "joint":
            self._joint_step(ctx)
            return
        role_scores = []
        next_representatives = []
        for role in range(2):
            scores = []
            # Common partner panel for fair comparison of this role's candidates.
            partner_indices = self.rng.integers(self.population_size, size=self.collaborators - 1)
            partners = [self.representatives[1 - role]] + [self.populations[1 - role, j] for j in partner_indices]
            for index, genome in enumerate(self.populations[role]):
                shared = []
                for partner_index, partner in enumerate(partners):
                    team = np.empty((2, self.dimension))
                    team[role], team[1 - role] = genome, partner
                    result = ctx.evaluate(
                        team.ravel().tolist(),
                        lambda: cooperative_episode(team, seed=self.seed),
                        label=f"cooperative/g{self.generation}/r{role}/c{index}/partner{partner_index}",
                    )
                    shared.append(result["fitness"])
                    # Partner trials are measured complete teams too; retain
                    # their best without changing mean-credit reproduction.
                    if self.best_fitness is None or result["fitness"] > self.best_fitness:
                        self.best_fitness, self.best_team = result["fitness"], team.copy()
                scores.append(float(np.mean(shared)))
                ctx.record({"event": "cooperative_credit", "generation": self.generation,
                            "role": role, "candidate": index, "partner_fitnesses": shared,
                            "shared_fitness": scores[-1], "partner_dependence": float(np.ptp(shared))})
            role_scores.append(scores)
            next_representatives.append(self.populations[role, int(np.argmax(scores))].copy())
        self.representatives = np.asarray(next_representatives)
        result = ctx.evaluate(
            self.representatives.ravel().tolist(),
            lambda: cooperative_episode(self.representatives, seed=self.seed),
            label=f"cooperative/g{self.generation}/assembled_team",
        )
        if self.best_fitness is None or result["fitness"] > self.best_fitness:
            self.best_fitness = result["fitness"]
            self.best_team = self.representatives.copy()
        for role in range(2):
            self.populations[role] = _breed(self.populations[role], role_scores[role], self.rng, self.sigma)
        self._finish(ctx, {"event": "cooperative_generation", "generation": self.generation,
                           "team_fitness": result["fitness"], "best_fitness": self.best_fitness})

    def summary(self):
        return {"method": "cooperative", "generation": self.generation,
                "best_fitness": self.best_fitness, "team_size": 2,
                "team_mode": self.team_mode,
                "credit_assignment": ("mean shared team reward over representative and sampled collaborators"
                                      if self.team_mode == "coevolution" else "direct complete-team reward"),
                "best_genome": None if self.best_team is None else self.best_team.tolist(),
                "history": self.history}

    def replay(self, seed=None):
        if self.best_team is None:
            raise ValueError("no evaluated team available")
        return cooperative_episode(self.best_team, seed=self.seed if seed is None else seed)


# Rows are the first player's action; rock beats scissors, paper beats rock.
PAYOFF = np.array([[0.0, -1.0, 1.0], [1.0, 0.0, -1.0], [-1.0, 1.0, 0.0]])


def game_policy(genome, own, opponent):
    logits = 3.0 * neural_action(genome, np.r_[own, opponent], inputs=6, outputs=3)
    p = np.exp(logits - logits.max())
    return p / p.sum()


def competitive_match(first, second, rounds=24):
    """Expected payoffs of interacting recurrent-observation mixed strategies."""
    a = b = np.ones(3) / 3
    rewards, behaviors = [], []
    for _ in range(rounds):
        new_a = game_policy(first, a, b)
        new_b = game_policy(second, b, a)
        rewards.append(float(new_a @ PAYOFF @ new_b))
        behaviors.append(new_a)
        a, b = new_a, new_b
    return measurement(np.mean(rewards), np.mean(behaviors, axis=0), rounds=rounds)


def fixed_opponents():
    """Run-independent neural validation panel; includes all pure strategies."""
    dimension = network_size(6, outputs=3)
    panel = []
    for action in range(3):
        g = np.zeros(dimension)
        g[-3:] = -2
        g[-3 + action] = 2
        panel.append(g)
    independent_rng = np.random.default_rng(732451)
    panel.extend(independent_rng.normal(0, 0.9, (6, dimension)))
    return np.asarray(panel)


def competitive_panel(genome, opponents):
    results = [competitive_match(genome, opponent) for opponent in opponents]
    scores = [r["fitness"] for r in results]
    return measurement(np.mean(scores), np.mean([r["descriptor"] for r in results], axis=0),
                       opponent_scores=scores, worst_score=float(min(scores)), game_matches=len(scores))


def cycling_diagnostic(previous, current, tolerance=0.01):
    """A relative-fitness gain with fixed-panel regression is a warning, not proof."""
    return bool(previous is not None and current["relative_fitness"] > previous["relative_fitness"]
                and current["absolute_worst"] < previous["absolute_worst"] - tolerance)


class CompetitiveEngine(_Engine):
    def __init__(self, spec):
        super().__init__(spec)
        self.dimension = network_size(6, outputs=3)
        self.population = self.rng.normal(0, 0.65, (self.population_size, self.dimension))
        self.hall_of_fame = []
        self.archive_limit = int(self.params.get("archive_size", 8))
        if self.archive_limit < 0:
            raise ValueError("archive_size must be nonnegative; zero is the no-history ablation")
        self.validation_panel = fixed_opponents()
        self.best_genome = None
        self.best_fitness = None
        self.best_mean = None
        self.game_matches = 0

    def step(self, ctx):
        if self.done:
            return
        # Freeze the contemporary panel before selection; all candidates face it.
        indices = self.rng.choice(self.population_size, min(3, self.population_size), replace=False)
        opponents = [self.population[j].copy() for j in indices] + [g.copy() for g in self.hall_of_fame]
        scores = []
        for index, genome in enumerate(self.population):
            result = ctx.evaluate(genome.tolist(), lambda: competitive_panel(genome, opponents),
                                  label=f"competitive/g{self.generation}/relative/{index}")
            scores.append(result["fitness"])
            self.game_matches += len(opponents)
        champion = self.population[int(np.argmax(scores))].copy()
        absolute = ctx.evaluate(champion.tolist(), lambda: competitive_panel(champion, self.validation_panel),
                                label=f"competitive/g{self.generation}/fixed_validation")
        worst = absolute["metrics"]["worst_score"]
        self.game_matches += len(self.validation_panel)
        if self.best_fitness is None or worst > self.best_fitness:
            self.best_fitness, self.best_mean = worst, absolute["fitness"]
            self.best_genome = champion.copy()
        row = {"event": "competitive_generation", "generation": self.generation,
               "relative_fitness": float(max(scores)), "absolute_mean": absolute["fitness"],
               "absolute_worst": worst, "absolute_opponent_scores": absolute["metrics"]["opponent_scores"],
               "validation_panel": "fixed-neural-rps-v1-seed732451", "historical_opponents": len(self.hall_of_fame),
               "behavior": absolute["descriptor"]}
        row["cycling_warning"] = cycling_diagnostic(self.history[-1] if self.history else None, row)
        # Log cross-play with the previous champion separately from absolute checks.
        if self.hall_of_fame:
            previous = self.hall_of_fame[-1]
            match = ctx.evaluate(champion.tolist(), lambda: competitive_match(champion, previous),
                                 label=f"competitive/g{self.generation}/previous_champion")
            row["versus_previous_champion"] = match["fitness"]
            self.game_matches += 1
        row["game_matches"] = self.game_matches
        row["training_panel_size"] = len(opponents)
        if self.archive_limit:
            self.hall_of_fame.append(champion)
            self.hall_of_fame = self.hall_of_fame[-self.archive_limit:]
        self.population = _breed(self.population, scores, self.rng, self.sigma)
        self._finish(ctx, row)

    def summary(self):
        return {"method": "competitive", "generation": self.generation,
                "best_fitness": self.best_fitness, "best_fixed_panel_mean": self.best_mean,
                "selection_metric": "relative mean payoff against current and historical opponents",
                "saved_best_metric": "worst payoff against unchanged fixed neural panel",
                "best_genome": None if self.best_genome is None else self.best_genome.tolist(),
                "historical_opponents": len(self.hall_of_fame), "history": self.history,
                "archive_capacity": self.archive_limit,
                "game_matches": self.game_matches, "game_rounds": 24 * self.game_matches,
                "limitation": "Fixed-panel regression warns of cycling; this panel does not prove global progress."}

    def replay(self, seed=None):
        if self.best_genome is None:
            raise ValueError("no evaluated champion available")
        result = competitive_panel(self.best_genome, self.validation_panel)
        result["metrics"]["mean_payoff"] = result["fitness"]
        result["fitness"] = result["metrics"]["worst_score"]
        return result


ENV_LOW = np.array([0.1, 0.4, -0.3, 0.05])
ENV_HIGH = np.array([0.9, 2.0, 0.3, 0.3])


def environment_descriptor(environment):
    return (np.asarray(environment) - ENV_LOW) / (ENV_HIGH - ENV_LOW)


def terrain_episode(genome, environment, *, seed=0, horizon=48):
    """Neural feedback control with evolving target amplitude/frequency, wind, drag.

    The target is a smooth course; there are no simulated legs or obstacle physics.
    The descriptor describes dynamics, not a claim about terrain geometry.
    """
    amplitude, frequency, wind, drag = np.asarray(environment)
    phases = np.random.default_rng(seed).uniform(-np.pi, np.pi, 3)
    errors, efforts, final_positions = [], [], []
    for phase in phases:
        x, v = 0.0, 0.0
        for step in range(horizon):
            t = step * 0.08
            target = amplitude * np.sin(frequency * t + phase)
            target_velocity = amplitude * frequency * np.cos(frequency * t + phase)
            action = float(neural_action(genome, [target - x, v, target_velocity, wind, 1.0])[0])
            v = (1 - drag) * v + 0.18 * action + 0.06 * wind
            x += 0.08 * v
            errors.append((target - x) ** 2)
            efforts.append(action ** 2)
        final_positions.append(x)
    mse, effort = float(np.mean(errors)), float(np.mean(efforts))
    return measurement(1 - mse - 0.02 * effort, environment_descriptor(environment),
                       mse=mse, effort=effort, final_positions=final_positions)


@dataclass
class EnvironmentAgentPair:
    identifier: int
    parent: int | None
    environment: np.ndarray
    genome: np.ndarray
    born: int
    fitness: float | None = None


class PoetEngine(_Engine):
    """A finite POET-style experiment with true optimization and both transfers."""
    def __init__(self, spec):
        super().__init__(spec)
        self.dimension = network_size(5)
        self.max_pairs = int(self.params.get("max_pairs", 4))
        self.mutation_interval = int(self.params.get("environment_interval", 1))
        self.transfer_interval = int(self.params.get("transfer_interval", 1))
        self.transfer_mode = self.params.get("transfer_mode", "both")
        if self.transfer_mode not in ("none", "direct", "both"):
            raise ValueError("transfer_mode must be none, direct, or both")
        self.environment_sigma = float(self.params.get("environment_sigma", 0.16))
        self.novelty_threshold = float(self.params.get("novelty_threshold", 0.08))
        self.minimum = float(self.params.get("minimal_fitness", 0.25))
        self.maximum = float(self.params.get("maximal_fitness", 0.995))
        self.reproduction_threshold = float(self.params.get("reproduction_threshold", 0.5))
        self.es_learning_rate = float(self.params.get("es_learning_rate", 0.12))
        if self.max_pairs < 2 or min(self.mutation_interval, self.transfer_interval) < 1:
            raise ValueError("max_pairs >= 2 and positive environment/transfer intervals required")
        if not self.minimum < self.maximum or self.environment_sigma <= 0 or self.novelty_threshold <= 0:
            raise ValueError("minimal_fitness < maximal_fitness and positive mutation/novelty thresholds required")
        self.pairs = [EnvironmentAgentPair(0, None, np.array([0.25, 0.7, 0.0, 0.12]),
                                         self.rng.normal(0, 0.25, self.dimension), 0)]
        self.environment_archive = [self.pairs[0].environment.copy()]
        self.ancestry = [{"id": 0, "parent": None, "born": 0, "environment": self.pairs[0].environment.tolist()}]
        self.next_id = 1
        self.transfer_attempts = 0
        self.adapted_transfer_attempts = 0
        self.accepted_transfers = 0
        self.best_genome = None
        self.best_environment = None
        self.best_fitness = None

    def _evaluate(self, ctx, genome, environment, label):
        # The environment is part of the journal identity for the same policy.
        return ctx.evaluate(np.r_[genome, environment].tolist(),
                            lambda: terrain_episode(genome, environment, seed=self.seed), label=label)

    def _optimize(self, ctx, genome, environment, label, base_fitness=None, perturbations=None):
        """One antithetic ES update, confirmed alongside the best sampled policy."""
        if base_fitness is None:
            base_fitness = self._evaluate(ctx, genome, environment, label + "/base")["fitness"]
        count = max(2, (self.population_size if perturbations is None else perturbations) // 2)
        noises = self.rng.normal(size=(count, self.dimension))
        plus_scores, minus_scores = [], []
        best, best_score = genome.copy(), base_fitness
        for index, noise in enumerate(noises):
            for sign, values in [(1, plus_scores), (-1, minus_scores)]:
                candidate = genome + sign * self.sigma * noise
                score = self._evaluate(ctx, candidate, environment, f"{label}/probe{index}/{sign}")["fitness"]
                values.append(score)
                if score > best_score:
                    best, best_score = candidate.copy(), score
        differences = np.asarray(plus_scores) - np.asarray(minus_scores)
        gradient = differences @ noises / (2 * count * self.sigma)
        proposal = genome + self.es_learning_rate * gradient
        proposal_score = self._evaluate(ctx, proposal, environment, label + "/es_proposal")["fitness"]
        if proposal_score > best_score:
            best, best_score = proposal, proposal_score
        ctx.record({"event": "poet_policy_optimization", "generation": self.generation, "label": label,
                    "before": base_fitness, "after": best_score, "gradient_norm": float(np.linalg.norm(gradient)),
                    "genome_change": float(np.linalg.norm(best - genome))})
        return best, float(best_score)

    def _generate_environments(self, ctx):
        proposals = []
        for parent in list(self.pairs):
            if parent.fitness is None or parent.fitness < self.reproduction_threshold:
                continue
            normalized = environment_descriptor(parent.environment)
            mutated = np.clip(normalized + self.rng.normal(0, self.environment_sigma, 4), 0, 1)
            environment = ENV_LOW + mutated * (ENV_HIGH - ENV_LOW)
            distances = [np.linalg.norm(mutated - environment_descriptor(old)) for old in self.environment_archive]
            novelty = float(min(distances))
            result = self._evaluate(ctx, parent.genome, environment,
                                    f"poet/g{self.generation}/child_of{parent.identifier}/admissibility")
            admissible = self.minimum < result["fitness"] < self.maximum
            novel = novelty >= self.novelty_threshold
            ctx.record({"event": "poet_environment_filter", "generation": self.generation,
                        "parent": parent.identifier, "environment": environment.tolist(), "fitness": result["fitness"],
                        "admissible": admissible, "novel": novel, "novelty": novelty})
            if admissible and novel:
                proposals.append((novelty, parent, environment, result["fitness"]))
        for novelty, parent, environment, score in sorted(proposals, key=lambda item: -item[0]):
            # Recheck against children admitted earlier in the same batch.
            novelty = min(float(np.linalg.norm(environment_descriptor(environment) - environment_descriptor(old)))
                          for old in self.environment_archive)
            if novelty < self.novelty_threshold:
                continue
            child = EnvironmentAgentPair(self.next_id, parent.identifier, environment,
                                         parent.genome.copy(), self.generation, score)
            self.next_id += 1
            self.pairs.append(child)
            self.environment_archive.append(environment.copy())
            entry = {"id": child.identifier, "parent": child.parent, "born": child.born,
                     "environment": environment.tolist(), "novelty": novelty}
            self.ancestry.append(entry)
            ctx.record({"event": "poet_environment_admitted", **entry})
            if len(self.pairs) > self.max_pairs:
                retired = self.pairs.pop(0)
                ctx.record({"event": "poet_environment_retired", "id": retired.identifier,
                            "generation": self.generation, "reason": "oldest pair retired at capacity"})

    def _transfer(self, ctx):
        sources = [(pair.identifier, pair.genome.copy()) for pair in self.pairs]
        for target in self.pairs:
            for source_id, source_genome in sources:
                if source_id == target.identifier:
                    continue
                label = f"poet/g{self.generation}/transfer{source_id}_to{target.identifier}"
                direct = self._evaluate(ctx, source_genome, target.environment, label + "/direct")["fitness"]
                self.transfer_attempts += 1
                if self.transfer_mode == "both":
                    adapted, adapted_score = self._optimize(ctx, source_genome, target.environment,
                                                            label + "/adapted", direct, perturbations=4)
                    self.adapted_transfer_attempts += 1
                else:
                    adapted, adapted_score = source_genome, direct
                baseline = target.fitness
                accepted = max(direct, adapted_score) > baseline
                mode = "adapted" if adapted_score > direct else "direct"
                if accepted:
                    target.genome = adapted.copy() if mode == "adapted" else source_genome.copy()
                    target.fitness = max(direct, adapted_score)
                    self.accepted_transfers += 1
                ctx.record({"event": "poet_transfer", "generation": self.generation,
                            "source": source_id, "target": target.identifier, "direct_fitness": direct,
                            "adapted_fitness": adapted_score, "incumbent_fitness": baseline,
                            "adaptation_attempted": self.transfer_mode == "both",
                            "adaptation_distance": float(np.linalg.norm(adapted - source_genome)),
                            "accepted": accepted, "accepted_mode": mode if accepted else None})

    def step(self, ctx):
        if self.done:
            return
        for pair in self.pairs:
            pair.genome, pair.fitness = self._optimize(
                ctx, pair.genome, pair.environment, f"poet/g{self.generation}/pair{pair.identifier}", pair.fitness)
        if self.generation % self.mutation_interval == 0:
            self._generate_environments(ctx)
        if self.transfer_mode != "none" and self.generation % self.transfer_interval == 0:
            self._transfer(ctx)
        for pair in self.pairs:
            if self.best_fitness is None or pair.fitness > self.best_fitness:
                self.best_genome, self.best_environment = pair.genome.copy(), pair.environment.copy()
                self.best_fitness = pair.fitness
        self._finish(ctx, {"event": "poet_generation", "generation": self.generation,
                           "active_pairs": len(self.pairs), "environments_discovered": len(self.environment_archive),
                           "transfer_attempts": self.transfer_attempts, "accepted_transfers": self.accepted_transfers,
                           "pair_fitnesses": {str(pair.identifier): pair.fitness for pair in self.pairs}})

    def summary(self):
        return {"method": "poet", "generation": self.generation, "best_fitness": self.best_fitness,
                "best_genome": None if self.best_genome is None else self.best_genome.tolist(),
                "best_environment": None if self.best_environment is None else self.best_environment.tolist(),
                "active_pairs": [{"id": p.identifier, "parent": p.parent, "environment": p.environment.tolist(),
                                  "fitness": p.fitness, "genome": p.genome.tolist()} for p in self.pairs],
                "ancestry": self.ancestry, "direct_transfer_attempts": self.transfer_attempts,
                "adapted_transfer_attempts": self.adapted_transfer_attempts, "accepted_transfers": self.accepted_transfers,
                "transfer_mode": self.transfer_mode,
                "history": self.history,
                "limitation": "Bounded POET-style tracking domain; no unlimited open-endedness or BipedalWalker reproduction claim.",
                "best_metric_scope": "maximum measured fitness over paired tasks; scores do not rank task difficulty"}

    def replay(self, seed=None):
        if self.best_genome is None:
            raise ValueError("no evaluated pair available")
        return terrain_episode(self.best_genome, self.best_environment, seed=self.seed if seed is None else seed)


def prescription_reward(context, action):
    optimum = 0.6 * np.sin(np.pi * np.asarray(context)) + 0.2 * np.asarray(context)
    return 1 - (np.asarray(action) - optimum) ** 2 - 0.03 * np.asarray(action) ** 2


def prescription_actions(genome, contexts):
    return neural_action(genome, np.asarray(contexts).reshape(-1, 1), inputs=1, hidden=6).reshape(-1)


def prescription_episode(genome, contexts):
    actions = prescription_actions(genome, contexts)
    rewards = prescription_reward(contexts, actions)
    return measurement(np.mean(rewards), [np.mean(actions), np.std(actions)],
                       contexts=np.asarray(contexts).tolist(), actions=actions.tolist(), rewards=rewards.tolist())


class RewardSurrogate:
    """Small random-feature tanh neural predictor with a learned ridge output.

    Hidden features stay fixed; output weights learn context/action -> reward.
    Deliberately finite data and capacity make its prediction imperfect.
    """
    def __init__(self, rng, hidden=20, ridge=0.03):
        self.weights = rng.normal(0, 1.5, (2, hidden))
        self.bias = rng.normal(0, 0.5, hidden)
        self.output = np.zeros(hidden + 1)
        self.ridge = ridge

    def features(self, inputs):
        hidden = np.tanh(np.asarray(inputs) @ self.weights + self.bias)
        return np.c_[hidden, np.ones(len(hidden))]

    def fit(self, inputs, rewards):
        features = self.features(inputs)
        self.output = np.linalg.solve(features.T @ features + self.ridge * np.eye(features.shape[1]),
                                      features.T @ np.asarray(rewards))

    def predict(self, inputs):
        return self.features(inputs) @ self.output


class SurrogateEngine(_Engine):
    def __init__(self, spec):
        super().__init__(spec)
        self.dimension = network_size(1, hidden=6)
        self.population = self.rng.normal(0, 0.6, (self.population_size, self.dimension))
        self.model = RewardSurrogate(self.rng)
        self.search_mode = self.params.get("search_mode", "surrogate")
        if self.search_mode not in ("surrogate", "direct"):
            raise ValueError("search_mode must be surrogate or direct")
        self.contexts = np.linspace(-1, 1, 33)
        self.inputs, self.rewards = [], []
        self.bootstrap_samples = int(self.params.get("bootstrap_samples", 12))
        self.confirmations = int(self.params.get("true_confirmations", 2))
        if self.bootstrap_samples < 4 or not 1 <= self.confirmations < self.population_size:
            raise ValueError("bootstrap_samples >= 4 and 1 <= true_confirmations < population_size required")
        self.predicted_evaluations = 0
        self.true_policy_evaluations = 0
        self.true_outcome_queries = 0
        self.best_genome = None
        self.best_fitness = None
        self.initialized = False

    def _bootstrap(self, ctx):
        for index in range(self.bootstrap_samples):
            context, action = self.rng.uniform(-1, 1, 2)
            result = ctx.evaluate([float(context), float(action)],
                                  lambda: measurement(prescription_reward(context, action), [context, action]),
                                  label=f"surrogate/bootstrap/{index}")
            self.inputs.append([float(context), float(action)])
            self.rewards.append(result["fitness"])
            self.true_outcome_queries += 1
        self.model.fit(self.inputs, self.rewards)
        self.initialized = True

    def _prediction(self, genome):
        actions = prescription_actions(genome, self.contexts)
        predictions = self.model.predict(np.c_[self.contexts, actions])
        return measurement(np.mean(predictions), [np.mean(actions), np.std(actions)],
                           evaluation_kind="surrogate_prediction", predicted_rewards=predictions.tolist())

    def _direct_step(self, ctx):
        """Baseline: Gaussian evolution using true reward for every candidate."""
        scores = []
        for index, genome in enumerate(self.population):
            result = ctx.evaluate(genome.tolist(), lambda: prescription_episode(genome, self.contexts),
                                  label=f"surrogate/g{self.generation}/direct/{index}")
            scores.append(result["fitness"])
            self.true_policy_evaluations += 1
            self.true_outcome_queries += len(self.contexts)
            if self.best_fitness is None or result["fitness"] > self.best_fitness:
                self.best_fitness, self.best_genome = result["fitness"], genome.copy()
        self.population = _breed(self.population, scores, self.rng, self.sigma)
        self._finish(ctx, {"event": "surrogate_direct_generation", "generation": self.generation,
                           "best_true_fitness": self.best_fitness,
                           "true_policy_evaluations": self.true_policy_evaluations,
                           "true_outcome_queries": self.true_outcome_queries})

    def step(self, ctx):
        if self.done:
            return
        if self.search_mode == "direct":
            self._direct_step(ctx)
            return
        if not self.initialized:
            self._bootstrap(ctx)
        predicted = []
        for index, genome in enumerate(self.population):
            result = ctx.evaluate(genome.tolist(), lambda: self._prediction(genome),
                                  label=f"surrogate/g{self.generation}/predicted/{index}", kind="predicted")
            predicted.append(result["fitness"])
            self.predicted_evaluations += 1
        ranked = list(np.argsort(-np.asarray(predicted), kind="stable"))
        selected = ranked[:self.confirmations]
        # One exploration policy prevents conditioning all new data on surrogate maxima.
        remaining = ranked[self.confirmations:]
        selected.append(remaining[int(self.rng.integers(len(remaining)))])
        prediction_errors = []
        confirmations = []
        for index in selected:
            genome = self.population[index]
            result = ctx.evaluate(genome.tolist(), lambda: prescription_episode(genome, self.contexts),
                                  label=f"surrogate/g{self.generation}/true/{index}")
            metrics = result["metrics"]
            observed_inputs = np.c_[metrics["contexts"], metrics["actions"]]
            point_predictions = self.model.predict(observed_inputs)
            prediction_errors.extend((point_predictions - np.asarray(metrics["rewards"])).tolist())
            self.inputs.extend(observed_inputs.tolist())
            self.rewards.extend(metrics["rewards"])
            self.true_policy_evaluations += 1
            self.true_outcome_queries += len(metrics["rewards"])
            confirmations.append({"candidate": int(index), "prediction": predicted[index],
                                  "true_fitness": result["fitness"], "exploration": bool(index == selected[-1])})
            if self.best_fitness is None or result["fitness"] > self.best_fitness:
                self.best_fitness = result["fitness"]
                self.best_genome = genome.copy()
        # Retraining occurs only after measuring predictive errors, avoiding leakage.
        self.model.fit(self.inputs, self.rewards)
        self.population = _breed(self.population, predicted, self.rng, self.sigma)
        self._finish(ctx, {"event": "surrogate_generation", "generation": self.generation,
                           "confirmation": confirmations, "best_true_fitness": self.best_fitness,
                           "confirmation_mae_before_refit": float(np.mean(np.abs(prediction_errors))),
                           "training_outcomes": len(self.rewards), "predicted_evaluations": self.predicted_evaluations,
                           "true_policy_evaluations": self.true_policy_evaluations,
                           "true_outcome_queries": self.true_outcome_queries})

    def summary(self):
        return {"method": "surrogate", "generation": self.generation, "best_fitness": self.best_fitness,
                "search_mode": self.search_mode,
                "best_genome": None if self.best_genome is None else self.best_genome.tolist(),
                "saved_best_metric": "measured true-environment mean reward; never predicted fitness",
                "predictor": ("20 tanh random hidden features with learned ridge-regression output"
                              if self.search_mode == "surrogate" else None),
                "predicted_evaluations": self.predicted_evaluations,
                "true_policy_evaluations": self.true_policy_evaluations,
                "true_outcome_queries": self.true_outcome_queries, "history": self.history,
                "limitation": "Bounded synthetic prescription domain; no real-world deployment or sample-efficiency superiority claim."}

    def replay(self, seed=None):
        if self.best_genome is None:
            raise ValueError("no truly evaluated controller available")
        return prescription_episode(self.best_genome, self.contexts)


METHODS = {"cooperative": CooperativeEngine, "competitive": CompetitiveEngine,
           "poet": PoetEngine, "surrogate": SurrogateEngine}

TARGETS = {"cooperative": ["cooperative-tracking"], "competitive": ["competitive-rps"],
           "poet": ["terrain-tracking"], "surrogate": ["surrogate-control"]}
