"""Population searches over real neural controllers; all fitness goes through ctx.

These small reference environments are CPU acceptance tasks, not benchmark claims.
Fitness is maximized throughout this module; adapters negate it for minimizers.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from typing import Any

import numpy as np


TARGETS = {"xor": (2, 1), "cartpole": (4, 1), "navigation": (4, 2)}


def target_name(target: str) -> str:
    aliases = {"deceptive_navigation": "navigation", "deceptive_maze": "navigation",
               "CartPole-v1": "cartpole", "cart_pole": "cartpole"}
    target = aliases.get(target, target)
    if target not in TARGETS:
        raise ValueError(f"Unknown controller target {target!r}; choose {list(TARGETS)}")
    return target


def parameter_count(target: str, hidden: int = 4) -> int:
    n_in, n_out = TARGETS[target_name(target)]
    return (n_in + 1) * hidden + (hidden + 1) * n_out


def flat_policy(weights, target: str, hidden: int = 4):
    target = target_name(target)
    n_in, n_out = TARGETS[target]
    weights = np.asarray(weights, dtype=float)
    if weights.size != parameter_count(target, hidden):
        raise ValueError("Controller weight count does not match its topology")
    cut = (n_in + 1) * hidden
    first = weights[:cut].reshape(n_in + 1, hidden)
    second = weights[cut:].reshape(hidden + 1, n_out)

    def policy(observation):
        h = np.tanh(np.r_[observation, 1.0] @ first)
        output = np.r_[h, 1.0] @ second
        return 1 / (1 + np.exp(-np.clip(output, -60, 60))) if target == "xor" else np.tanh(output)

    return policy


def evaluate_policy(policy, target: str, seed: int, parameters: dict | None = None) -> dict:
    """Execute XOR, classic CartPole equations, or a wall-deceptive 2-D maze."""
    parameters = parameters or {}
    target = target_name(target)
    if target == "xor":
        inputs = np.array([[0, 0], [0, 1], [1, 0], [1, 1]], dtype=float)
        outputs = np.array([float(np.asarray(policy(x))[0]) for x in inputs])
        desired = np.array([0., 1., 1., 0.])
        loss = float(np.mean((outputs - desired) ** 2))
        return {"fitness": 1.0 - loss, "descriptor": outputs[[1, 2]].tolist(),
                "constraints": bool(np.isfinite(outputs).all()),
                "metrics": {"mse": loss, "accuracy": float(np.mean((outputs >= .5) == desired)),
                            "predictions": outputs.tolist(), "episodes": 1}}
    if target == "cartpole":
        returns, descriptors = [], []
        episodes = int(parameters.get("episodes", 3))
        horizon = int(parameters.get("horizon", 200))
        for episode in range(episodes):
            state = np.random.default_rng(seed + episode).uniform(-.05, .05, 4)
            positions, angles = [], []
            for step in range(horizon):
                x, x_dot, theta, theta_dot = state
                action = float(np.asarray(policy(state))[0])
                force = 10.0 if action >= 0 else -10.0
                costheta, sintheta = math.cos(theta), math.sin(theta)
                temp = (force + .05 * theta_dot ** 2 * sintheta) / 1.1
                theta_acc = (9.8 * sintheta - costheta * temp) / (.5 * (4 / 3 - .1 * costheta ** 2 / 1.1))
                x_acc = temp - .05 * theta_acc * costheta / 1.1
                state = np.array([x + .02*x_dot, x_dot + .02*x_acc,
                                  theta + .02*theta_dot, theta_dot + .02*theta_acc])
                positions.append(state[0]); angles.append(state[2])
                if abs(state[0]) > 2.4 or abs(state[2]) > 12 * math.pi / 180:
                    break
            returns.append(step + 1)
            descriptors.append([float(np.mean(positions)), float(np.mean(angles))])
        return {"fitness": float(np.mean(returns)), "descriptor": np.mean(descriptors, axis=0).tolist(),
                "constraints": True, "metrics": {"returns": returns, "episodes": episodes,
                                                 "horizon": horizon}}
    # The wall blocks the direct route from left to right; the opening is at y>=.8.
    rng = np.random.default_rng(seed)
    position = np.array([.1, .5]) + rng.uniform(-.01, .01, 2)
    goal = np.array([.9, .5]); path = [position.tolist()]; collisions = 0
    horizon = int(parameters.get("horizon", 80))
    for _ in range(horizon):
        observation = np.r_[position, goal-position]
        velocity = np.clip(np.asarray(policy(observation), dtype=float), -1, 1)
        proposal = np.clip(position + .04 * velocity, 0, 1)
        crossing = (position[0] < .5 <= proposal[0]) or (proposal[0] < .5 <= position[0])
        crossing_y = position[1] + (.5-position[0]) * (proposal[1]-position[1]) / (proposal[0]-position[0]) if crossing else 1.
        if crossing and crossing_y < .8:
            proposal[0] = position[0]; collisions += 1
        position = proposal; path.append(position.tolist())
        if np.linalg.norm(position-goal) < .06:
            break
    distance = float(np.linalg.norm(position-goal))
    return {"fitness": -distance, "descriptor": position.tolist(), "constraints": True,
            "metrics": {"distance": distance, "success": distance < .06,
                        "collisions": collisions, "trajectory": path, "episodes": 1}}


def evaluate_controller(weights, target: str, seed: int, parameters: dict | None = None) -> dict:
    parameters = parameters or {}
    result = evaluate_policy(flat_policy(weights, target, int(parameters.get("hidden", 4))), target, seed, parameters)
    complexity = float(np.mean(np.square(weights)))
    result["objectives"] = [float(result["fitness"]), -complexity]
    result["metrics"]["weight_mean_square"] = complexity
    return result


def novelty_and_competition(descriptors, fitnesses, archive, k=5):
    """Mean k-neighbor distance and fraction of neighbors beaten on fitness."""
    descriptors = np.asarray(descriptors, dtype=float)
    fitnesses = np.asarray(fitnesses, dtype=float)
    archived_descriptors = np.array([r[0] for r in archive], dtype=float).reshape(-1, descriptors.shape[1])
    all_descriptors = np.vstack([descriptors, archived_descriptors])
    all_fitness = np.r_[fitnesses, [r[1] for r in archive]]
    novelty, local_competition = [], []
    for index, descriptor in enumerate(descriptors):
        distances = np.linalg.norm(all_descriptors-descriptor, axis=1)
        distances[index] = np.inf  # exclude this individual, not all duplicates
        neighbors = np.argsort(distances)[:min(k, len(all_descriptors)-1)]
        novelty.append(float(np.mean(distances[neighbors])) if len(neighbors) else 0.)
        local_competition.append(float(np.mean(fitnesses[index] > all_fitness[neighbors])) if len(neighbors) else 0.)
    return np.asarray(novelty), np.asarray(local_competition)


def pareto_order(maximize_scores):
    """NSGA-II nondomination followed by crowding distance within fronts."""
    from pymoo.util.nds.non_dominated_sorting import NonDominatedSorting
    values = np.asarray(maximize_scores, dtype=float)
    fronts = NonDominatedSorting().do(-values)
    ordering = []
    for front in fronts:
        crowding = np.zeros(len(front))
        for objective in range(values.shape[1]):
            order = np.argsort(values[front, objective], kind="stable")
            crowding[order[[0, -1]]] = np.inf
            span = np.ptp(values[front, objective])
            if span > 0 and len(front) > 2:
                crowding[order[1:-1]] += (values[front[order[2:]], objective] - values[front[order[:-2]], objective]) / span
        ordering.extend(front[np.argsort(-crowding, kind="stable")].tolist())
    return np.asarray(ordering, dtype=int)


class SearchEngine:
    """One complete population generation per step; pickleable checkpoint state."""
    def __init__(self, spec: dict):
        self.spec = copy.deepcopy(spec)
        self.method = spec["method"]
        self.target = target_name(spec.get("target", "xor"))
        self.parameters = dict(spec.get("parameters", {}))
        self.compute = dict(spec.get("compute", {}))
        self.seed = int(spec.get("seed", 0)); self.rng = np.random.default_rng(self.seed)
        self.size = int(spec.get("population_size", 16)); self.limit = int(spec.get("generations", 10))
        if self.size < 2 or self.limit < 1:
            raise ValueError("population_size>=2 and generations>=1 are required")
        if self.method == "es" and self.size % 2:
            raise ValueError("Antithetic ES requires an even population_size")
        self.dimension = parameter_count(self.target, int(self.parameters.get("hidden", 4)))
        self.sigma = float(self.parameters.get("sigma", .3))
        if self.sigma <= 0:
            raise ValueError("sigma must be positive")
        self.population = self.rng.normal(0, 1, (self.size, self.dimension))
        self.parents = [[] for _ in range(self.size)]
        self.mean = self.rng.normal(0, .1, self.dimension)
        self.generation = 0; self.done = False; self.best = None
        self.best_result = None; self.best_fitness = -float("inf")
        self.archive = []; self.history = []; self.optimizer = None
        if self.method == "cma_es":
            import cma
            self.optimizer = cma.CMAEvolutionStrategy(self.mean, self.sigma,
                {"popsize": self.size, "randn": self._randn, "seed": np.nan,
                 "verbose": -9, "verb_log": 0, "verb_disp": 0})
        elif self.method == "nsga2":
            from pymoo.algorithms.moo.nsga2 import NSGA2
            from pymoo.core.problem import Problem
            self.optimizer = NSGA2(pop_size=self.size)
            self.optimizer.setup(Problem(n_var=self.dimension, n_obj=2, xl=-5, xu=5),
                                 termination=("n_gen", self.limit+1), seed=self.seed, verbose=False)
        elif self.method == "map_elites":
            from ribs.archives import GridArchive
            ranges = [(0., 1.), (0., 1.)] if self.target != "cartpole" else [(-2.4, 2.4), (-.21, .21)]
            bins = int(self.parameters.get("bins", 8))
            self.qd_archive = GridArchive(solution_dim=self.dimension, dims=[bins, bins],
                                          ranges=ranges, seed=self.seed, qd_score_offset=-1 if self.target == "navigation" else 0)

    def _randn(self, *shape):
        return self.rng.standard_normal(shape)

    def _genome(self, weights):
        return {"encoding": "direct_mlp", "target": self.target,
                "hidden": int(self.parameters.get("hidden", 4)), "weights": np.asarray(weights).tolist()}

    def step(self, ctx):
        if self.done:
            return
        ask_population = None; perturbations = None
        if self.method == "cma_es":
            self.population = np.asarray(self.optimizer.ask())
        elif self.method == "nsga2":
            ask_population = self.optimizer.ask()
            self.population = np.asarray(ask_population.get("X"))
        elif self.method == "es":
            perturbations = self.rng.normal(size=(self.size//2, self.dimension))
            self.population = np.vstack([self.mean + self.sigma*perturbations, self.mean - self.sigma*perturbations])
        elif self.method == "random_search":
            self.population = self.rng.normal(0, float(self.parameters.get("initial_scale", 1.)), (self.size, self.dimension))
        elif self.method == "fixed_controller":
            self.population = self.population[:1]
            self.parents = [[]]
        elif self.method == "map_elites" and len(self.qd_archive):
            elites = self.qd_archive.data("solution")
            selected = self.rng.integers(len(elites), size=self.size)
            self.population = elites[selected] + self.rng.normal(0, self.sigma, (self.size, self.dimension))
            self.parents = [["archive:" + hashlib.sha256(json.dumps(elites[i].tolist(), separators=(",", ":")).encode()).hexdigest()]
                            for i in selected]
        results = []
        if getattr(self, "compute", {}).get("backend", "reference") == "torch":
            from .accelerator_search import evaluate_controllers_batch
            batch_size = int(self.compute.get("batch_size", 32))
            if batch_size < 1:
                raise ValueError("compute.batch_size must be positive")
            for start in range(0, len(self.population), batch_size):
                chunk = self.population[start:start + batch_size]
                # Context dispatches uncached candidates before any tensor or
                # environment execution; cached slots never incur new compute.
                batch_results = ctx.evaluate_batch(
                    [self._genome(weights) for weights in chunk],
                    lambda indices, chunk=chunk: evaluate_controllers_batch(
                        chunk[indices], self.target, [self.seed] * len(indices),
                        self.parameters, compute=self.compute),
                    labels=[f"{self.method}:{self.generation}:{start + index}" for index in range(len(chunk))])
                for weights, result in zip(chunk, batch_results):
                    results.append(result)
                    if result["constraints"] and float(result["fitness"]) > self.best_fitness:
                        self.best_fitness = float(result["fitness"]); self.best = weights.copy()
                        self.best_result = copy.deepcopy(result)
        else:
            for index, weights in enumerate(self.population):
                result = ctx.evaluate(self._genome(weights),
                    lambda w=weights: evaluate_controller(w, self.target, self.seed, self.parameters),
                    label=f"{self.method}:{self.generation}:{index}")
                results.append(result)
                if result["constraints"] and float(result["fitness"]) > self.best_fitness:
                    self.best_fitness = float(result["fitness"]); self.best = weights.copy()
                    self.best_result = copy.deepcopy(result)
        fitness = np.asarray([r["fitness"] if r["constraints"] else -1e12 for r in results], dtype=float)
        descriptors = np.asarray([r["descriptor"] for r in results], dtype=float)
        details: dict[str, Any] = {"kind": "generation", "method": self.method,
            "generation": self.generation, "best_fitness": self.best_fitness,
            "population_fitness": fitness.tolist(), "parents": self.parents}
        if self.method == "cma_es":
            self.optimizer.tell(self.population.tolist(), (-fitness).tolist())
            details["sigma"] = float(self.optimizer.sigma)
        elif self.method == "nsga2":
            ask_population.set("F", -np.asarray([r["objectives"] for r in results]))
            self.optimizer.tell(infills=ask_population)
            details["pareto_objectives"] = (-self.optimizer.opt.get("F")).tolist()
        elif self.method == "es":
            half = self.size//2
            scale = float(np.std(fitness))
            gradient = perturbations.T @ (fitness[:half]-fitness[half:]) / (2*half*self.sigma*max(scale, 1e-8))
            self.mean += float(self.parameters.get("learning_rate", .05))*gradient
            details["gradient_norm"] = float(np.linalg.norm(gradient))
            details["estimator"] = "antithetic_parameter_perturbation"
        elif self.method == "map_elites":
            insertion = self.qd_archive.add(self.population, fitness, descriptors)
            details.update(archive_size=len(self.qd_archive), coverage=float(self.qd_archive.stats.coverage),
                           insertion_status=np.asarray(insertion["status"]).tolist())
        elif self.method in {"random_search", "fixed_controller"}:
            details["selection"] = "none_independent_samples" if self.method == "random_search" else "none_one_fixed_initial_controller"
        else:
            if self.method in {"novelty", "nslc"}:
                novelty, competition = novelty_and_competition(descriptors, fitness, self.archive,
                                                               int(self.parameters.get("neighbors", 5)))
                order = np.argsort(-novelty, kind="stable") if self.method == "novelty" else pareto_order(np.c_[novelty, competition])
                threshold = float(self.parameters.get("novelty_threshold", .05))
                for index in range(len(fitness)):
                    if novelty[index] >= threshold or not self.archive:
                        digest = hashlib.sha256(json.dumps(self.population[index].tolist(), separators=(",", ":")).encode()).hexdigest()
                        self.archive.append((descriptors[index].tolist(), float(fitness[index]),
                                             self.population[index].copy(), f"archive:{self.generation}:{index}:{digest}"))
                self.archive = self.archive[-int(self.parameters.get("archive_capacity", 5000)):]
                details.update(novelty=novelty.tolist(), local_competition=competition.tolist(), archive_size=len(self.archive))
            else:
                order = np.argsort(-fitness, kind="stable")
            self._reproduce(order)
        self.history.append({key: value for key, value in details.items() if key != "parents"})
        ctx.record(details)
        self.generation += 1; self.done = self.method == "fixed_controller" or self.generation >= self.limit

    def _reproduce(self, order):
        count = max(2, self.size//2)
        eligible = np.asarray(order[:count])
        children = [self.population[order[0]].copy()]
        parent_ids = [[f"{self.generation}:{int(order[0])}"]]
        rate = float(self.parameters.get("mutation_rate", .2))
        def sample_parent():
            if (self.method in {"novelty", "nslc"} and self.archive and
                    self.rng.random() < float(self.parameters.get("archive_parent_probability", .25))):
                archived = self.archive[int(self.rng.integers(len(self.archive)))]
                return archived[2], archived[3]
            index = int(self.rng.choice(eligible))
            return self.population[index], f"{self.generation}:{index}"
        for _ in range(1, self.size):
            first, first_id = sample_parent(); second, second_id = sample_parent()
            child = np.where(self.rng.random(self.dimension) < .5, first, second)
            child += (self.rng.random(self.dimension) < rate)*self.rng.normal(0, self.sigma, self.dimension)
            children.append(child); parent_ids.append([first_id, second_id])
        self.population = np.asarray(children); self.parents = parent_ids

    def summary(self):
        out = {"method": self.method, "target": self.target, "generations": self.generation,
               "best_fitness": self.best_fitness if self.best is not None else None,
               "best_genome": self._genome(self.best) if self.best is not None else None,
               "best_result": self.best_result, "history": self.history}
        if self.method == "map_elites":
            out.update(archive_size=len(self.qd_archive), coverage=float(self.qd_archive.stats.coverage),
                       qd_score=float(self.qd_archive.stats.qd_score))
        if self.method == "nsga2" and self.generation:
            out["pareto_objectives"] = (-self.optimizer.opt.get("F")).tolist()
        return out

    def replay(self, seed=None):
        if self.best is None:
            raise ValueError("No evaluated controller to replay")
        if getattr(self, "compute", {}).get("backend", "reference") == "torch":
            from .accelerator_search import evaluate_controllers_batch
            return evaluate_controllers_batch(
                [self.best], self.target, [self.seed if seed is None else int(seed)],
                self.parameters, compute=self.compute)[0]
        return evaluate_controller(self.best, self.target, self.seed if seed is None else int(seed), self.parameters)


METHODS = {name: SearchEngine for name in ("fixed_controller", "random_search", "ga", "es", "cma_es", "nsga2", "novelty", "nslc", "map_elites")}
