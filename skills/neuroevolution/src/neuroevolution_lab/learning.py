"""Learning/evolution experiments with explicit inheritance and device kernels.

The small domains make the mechanisms inspectable. ERL is a DDPG-based reference
implementation; ``differentiable_qd`` is a gradient-archive variant, not CMA-MEGA.
CPU reference execution is preserved. Tensor backends batch dense populations;
ERL, plasticity and DQD retain their sequential candidate semantics. No evaluator
or callback is stored in an engine, so checkpoints are pickleable.
"""
from __future__ import annotations

import copy
import hashlib
import math
from typing import Any

import numpy as np
import torch
from torch import nn


def tensor_digest(value: np.ndarray | torch.Tensor) -> str:
    if isinstance(value, torch.Tensor):
        value = value.detach().cpu().numpy()
    return hashlib.sha256(np.asarray(value, dtype=np.float32).tobytes()).hexdigest()


def vector(model: nn.Module) -> np.ndarray:
    return torch.nn.utils.parameters_to_vector(model.parameters()).detach().cpu().numpy().copy()


def load_vector(model: nn.Module, weights: np.ndarray) -> None:
    expected = sum(p.numel() for p in model.parameters())
    if len(weights) != expected or not np.isfinite(weights).all():
        raise ValueError("finite neural parameter vector of the declared length required")
    parameter = next(model.parameters())
    torch.nn.utils.vector_to_parameters(torch.tensor(weights, dtype=parameter.dtype, device=parameter.device), model.parameters())


def make_mlp(inputs: int, hidden: int, outputs: int, seed: int, bounded: bool = False,
             device: str | torch.device = "cpu") -> nn.Module:
    with torch.random.fork_rng():
        torch.manual_seed(seed)
        layers: list[nn.Module] = [nn.Linear(inputs, hidden), nn.Tanh(), nn.Linear(hidden, outputs)]
        if bounded:
            layers.append(nn.Tanh())
        return nn.Sequential(*layers).to(device)


class Engine:
    """Common deterministic state; experiment runners own evaluation budgets."""

    method = "learning"
    target = ""

    def __init__(self, spec: dict[str, Any]):
        self.spec = copy.deepcopy(spec)
        if spec.get("target") not in (None, self.target):
            raise ValueError(f"{self.method} supports target {self.target!r}, not {spec.get('target')!r}")
        self.seed = int(spec.get("seed", 0))
        self.rng = np.random.default_rng(self.seed)
        self.population_size = int(spec.get("population_size", 6))
        self.generations = int(spec.get("generations", 3))
        if self.population_size < 2 or self.generations < 1:
            raise ValueError("population_size >= 2 and generations >= 1 required")
        self.parameters = spec.get("parameters", {})
        self.learning = spec.get("learning", {})
        self.parent_selection = self.parameters.get("parent_selection", "fitness")
        if self.parent_selection not in {"fitness", "random"}:
            raise ValueError("parent_selection must be fitness or random")
        self.generation = 0
        self.done = False
        self.best_fitness: float | None = None
        self.best_genome: np.ndarray | None = None
        self.history: list[dict[str, Any]] = []

    def _remember(self, genome: np.ndarray, result: dict[str, Any]) -> None:
        score = float(result["fitness"])
        if self.best_fitness is None or score > self.best_fitness:
            self.best_fitness, self.best_genome = score, genome.copy()

    def _finish(self, **details: Any) -> None:
        self.history.append({"generation": self.generation, **details})
        self.generation += 1
        self.done = self.generation >= self.generations

    def summary(self) -> dict[str, Any]:
        return {"method": self.method, "target": self.target, "generation": self.generation,
                "done": self.done, "best_fitness": self.best_fitness, "history": self.history,
                "implementation": "cpu_reference" if self.backend == "reference" else "torch_device",
                "compute": {**self.compute, "candidate_execution": self.batch_capability,
                            "population_storage": "host arrays; active numerical kernels on selected device",
                            "realized_batch_widths": getattr(self, "batch_widths", [])},
                "empirical_scope": "small synthetic domain",
                "parent_selection": self.parent_selection, "ancestry": getattr(self,"ancestry",[])}

    @property
    def compute(self) -> dict[str, Any]:
        # Derive rather than persist new required attributes: historical CPU
        # checkpoints predate the compute contract and remain replayable.
        return {"device": "cpu", "backend": "reference", "batch_size": 32,
                **self.spec.get("compute", {})}

    @property
    def backend(self) -> str:
        return self.compute["backend"]

    @property
    def device(self) -> torch.device:
        from .devices import resolve_device
        return resolve_device(self.compute)

    @property
    def batch_capability(self) -> str:
        if self.backend == "reference":
            return "serial reference"
        if self.method in {"gradient_refinement", "evolutionary_initialization", "model_merging", "parameter_evolution"}:
            return "population-batched tensor kernels"
        if self.method == "erl":
            return "serial rollouts; minibatched actor/critic training"
        return "serial candidates; device tensor kernels"

    def _population_evaluations(self, ctx, records, single_fn, batch_fn, labels):
        """Dispatch through the journal before running any candidate kernels."""
        if self.backend == "reference":
            for i, record in enumerate(records):
                yield i, ctx.evaluate(record, lambda j=i: single_fn(j), label=labels[i])
            return
        width = int(self.compute["batch_size"])
        if not hasattr(self, "batch_widths"):
            self.batch_widths = []
        for start in range(0, len(records), width):
            stop = min(start + width, len(records))
            def evaluate_pending(indices, offset=start):
                self.batch_widths.append(len(indices))
                return batch_fn([offset + i for i in indices])
            results = ctx.evaluate_batch(records[start:stop], evaluate_pending, labels=labels[start:stop])
            for offset, result in enumerate(results):
                yield start + offset, result

    def _offspring(self, genomes: np.ndarray, scores: list[float], sigma: float, ctx=None) -> np.ndarray:
        order = self.rng.permutation(len(genomes)) if self.parent_selection == "random" else np.argsort(scores)[::-1]
        parents = genomes[order[:max(1, len(genomes) // 2)]]
        children = [parents[0].copy()]
        parent_indices=[[int(order[0])]]
        while len(children) < self.population_size:
            a, b = self.rng.integers(0, len(parents), 2)
            mask = self.rng.random(parents.shape[1]) < .5
            child = np.where(mask, parents[a], parents[b])
            children.append(child + self.rng.normal(0, sigma, len(child)))
            parent_indices.append([int(order[a]),int(order[b])])
        offspring=np.asarray(children,dtype=np.float32)
        event={"event":"population_ancestry","generation":self.generation+1,"parents":parent_indices,
               "parent_tensor_hashes":[tensor_digest(g) for g in genomes],
               "offspring_tensor_hashes_before_profile_projection":[tensor_digest(g) for g in offspring],
               "note":"Indices identify the evaluated/inherited parent population; profile projection or actor reinsertion is recorded separately."}
        if not hasattr(self,"ancestry"): self.ancestry=[]
        self.ancestry.append(event)
        if ctx is not None: ctx.record(event)
        return offspring


def sine_task(seed: int, size: int = 24, task: tuple[float, float] = (1., 0.)) -> tuple[torch.Tensor, torch.Tensor]:
    rng = np.random.default_rng(seed)
    x = torch.tensor(rng.uniform(-math.pi, math.pi, (size, 1)), dtype=torch.float32)
    amplitude, phase = task
    return x, amplitude * torch.sin(x + phase)


def refine_sine(weights: np.ndarray, hidden: int, task: tuple[float, float], support_seed: int,
                query_seed: int, steps: int, lr: float,
                device: str | torch.device = "cpu") -> tuple[np.ndarray, dict[str, float]]:
    model = make_mlp(1, hidden, 1, 0, device=device)
    load_vector(model, weights)
    x, y = sine_task(support_seed, task=task)
    qx, qy = sine_task(query_seed, 48, task)
    x, y, qx, qy = (value.to(device) for value in (x, y, qx, qy))
    with torch.no_grad():
        initial = float(nn.functional.mse_loss(model(qx), qy))
    optimizer = torch.optim.SGD(model.parameters(), lr=lr)
    for _ in range(steps):
        optimizer.zero_grad()
        loss = nn.functional.mse_loss(model(x), y)
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), 10.)
        optimizer.step()
    with torch.no_grad():
        final = float(nn.functional.mse_loss(model(qx), qy))
    learned = vector(model)
    return learned, {"initial_query_mse": initial, "query_mse": final,
                     "parameter_delta_l2": float(np.linalg.norm(learned - weights)),
                     "gradient_steps": steps}


class GradientRefinement(Engine):
    method = "gradient_refinement"
    target = "sine_regression"

    def __init__(self, spec: dict[str, Any]):
        super().__init__(spec)
        self.hidden = int(self.parameters.get("hidden", 8))
        self.inheritance = self.learning.get("inheritance", "baldwinian").lower()
        if self.inheritance not in {"none", "baldwinian", "lamarckian"}:
            raise ValueError("inheritance must be none, baldwinian, or lamarckian")
        self.inner_steps = int(self.learning.get("inner_steps", 12))
        self.lr = float(self.learning.get("learning_rate", .03))
        if self.inner_steps < 0 or self.lr <= 0:
            raise ValueError("inner_steps must be nonnegative; learning_rate must be positive")
        self.population = np.stack([vector(make_mlp(1, self.hidden, 1, self.seed + i))
                                    for i in range(self.population_size)])
        self.last_inherited: np.ndarray | None = None
        self.best_phenotype: np.ndarray | None = None
        self.gradient_steps = 0

    def _result(self, weights: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
        steps = 0 if self.inheritance == "none" else self.inner_steps
        learned, metrics = refine_sine(weights, self.hidden, (1., 0.), self.seed + 101,
                                       self.seed + 102, steps, self.lr, self.device)
        return learned, self._refinement_record(weights, learned, metrics)

    @staticmethod
    def _refinement_record(weights, learned, metrics):
        result = {"fitness": -metrics["query_mse"], "descriptor": [metrics["parameter_delta_l2"]],
                  "constraints": True, "metrics": {**metrics, "selection_split": "validation",
                  "genotype_hash": tensor_digest(weights), "phenotype_hash": tensor_digest(learned),
                  "learned_weights": learned.tolist()}}
        return result

    def _batch_results(self, indices: list[int]) -> list[dict]:
        from .accelerator_learning import refine_sine_population
        steps = 0 if self.inheritance == "none" else self.inner_steps
        genomes = self.population[indices]
        learned, metrics = refine_sine_population(genomes, self.hidden, (1., 0.), self.seed + 101,
                                                  self.seed + 102, steps, self.lr, self.device)
        return [self._refinement_record(g, l, m) for g, l, m in zip(genomes, learned, metrics)]

    def step(self, ctx: Any) -> None:
        if self.done:
            return
        scores, inherited = [], []
        records = [{"kind": "neural_weights", "weights": genome.tolist(), "inheritance": self.inheritance}
                   for genome in self.population]
        labels = [f"refinement/{self.generation}/{i}" for i in range(len(records))]
        evaluations = self._population_evaluations(ctx, records, lambda i: self._result(self.population[i])[1],
                                                   self._batch_results, labels)
        for i, result in evaluations:
            genome = self.population[i]
            learned = np.asarray(result["metrics"]["learned_weights"], dtype=np.float32)
            transmitted = learned if self.inheritance == "lamarckian" else genome
            inherited.append(transmitted.copy())
            scores.append(result["fitness"])
            # Retain both hereditary genotype and acquired phenotype. Ordinary
            # refinement replays the frozen phenotype; meta-learning adapts anew.
            if self.best_fitness is None or result["fitness"] > self.best_fitness:
                self.best_phenotype = learned.copy()
            self._remember(genome, result)
            steps = result["metrics"]["gradient_steps"]
            self.gradient_steps += steps
            ctx.record({"event": "inheritance", "method": self.method, "candidate": i,
                        "mode": self.inheritance, "inner_updates": steps,
                        "genotype_hash": tensor_digest(genome), "learned_hash": tensor_digest(learned),
                        "transmitted_hash": tensor_digest(transmitted),
                        "adapted_task_hashes": [t["adapted_hash"] for t in result["metrics"].get("per_task", [])]})
        self.last_inherited = np.asarray(inherited)
        self.population = self._offspring(self.last_inherited, scores, float(self.parameters.get("mutation_sigma", .06)),ctx=ctx)
        self._finish(best_fitness=max(scores), inheritance=self.inheritance, inner_updates=self.gradient_steps)

    def summary(self) -> dict[str, Any]:
        return {**super().summary(), "inheritance": self.inheritance,
                "gradient_steps": self.gradient_steps, "hidden": self.hidden,
                "selected_phenotype_hash": tensor_digest(self.best_phenotype) if self.best_phenotype is not None else None}

    def replay(self, seed: int = 10000) -> dict[str, Any]:
        if self.best_genome is None or self.best_phenotype is None:
            raise ValueError("run at least one generation before replay")
        model = make_mlp(1, self.hidden, 1, 0, device=self.device)
        load_vector(model, self.best_phenotype)
        qx, qy = sine_task(seed, 48)
        qx, qy = qx.to(self.device), qy.to(self.device)
        with torch.no_grad():
            mse = float(nn.functional.mse_loss(model(qx), qy))
        delta = float(np.linalg.norm(self.best_phenotype-self.best_genome))
        split = "training_inputs" if seed == self.seed+101 else "validation_inputs" if seed == self.seed+102 else "heldout_inputs"
        return {"fitness": -mse, "descriptor": [delta], "constraints": True,
                "metrics": {"query_mse": mse, "parameter_delta_l2": delta, "split": split,
                "inheritance": self.inheritance, "seed": seed, "gradient_steps_during_replay": 0,
                "replay_kind": "frozen_selected_phenotype", "phenotype_hash": tensor_digest(self.best_phenotype)}}


class EvolutionaryInitialization(GradientRefinement):
    method = "evolutionary_initialization"
    target = "sine_task_family"

    def __init__(self, spec: dict[str, Any]):
        super().__init__(spec)
        if self.inheritance == "lamarckian":
            raise ValueError("initialization search inherits initial weights; use baldwinian or none")
        task_rng = np.random.default_rng(self.seed + 731)
        count = int(self.parameters.get("train_tasks", 3))
        if count < 1:
            raise ValueError("train_tasks must be positive")
        self.train_tasks = [(float(task_rng.uniform(.5, 1.5)), float(task_rng.uniform(-1., 1.)))
                            for _ in range(count)]
        self.train_task_ids = [f"train:{self.seed}:{i}" for i in range(count)]

    def _result(self, weights: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
        details = []
        steps = 0 if self.inheritance == "none" else self.inner_steps
        for i, task in enumerate(self.train_tasks):
            adapted, metrics = refine_sine(weights, self.hidden, task, self.seed + 1000 + 2*i,
                                           self.seed + 1001 + 2*i, steps, self.lr, self.device)
            metrics["adapted_hash"] = tensor_digest(adapted)
            metrics["task_parameters"] = list(task)
            details.append(metrics)
        mse = float(np.mean([m["query_mse"] for m in details]))
        return weights.copy(), {"fitness": -mse, "descriptor": [mse], "constraints": True,
            "metrics": {"query_mse": mse, "gradient_steps": steps * len(details),
            "learned_weights": weights.tolist(), "per_task": details,
            "train_task_ids": self.train_task_ids, "selection_split": "training_tasks_query_sets"}}

    def _batch_results(self, indices: list[int]) -> list[dict]:
        from .accelerator_learning import refine_sine_population
        genomes = self.population[indices]
        details = [[] for _ in indices]
        steps = 0 if self.inheritance == "none" else self.inner_steps
        for i, task in enumerate(self.train_tasks):
            adapted, metrics = refine_sine_population(genomes, self.hidden, task, self.seed+1000+2*i,
                                                      self.seed+1001+2*i, steps, self.lr, self.device)
            for candidate, (weights, record) in enumerate(zip(adapted, metrics)):
                details[candidate].append({**record, "adapted_hash": tensor_digest(weights),
                                           "task_parameters": list(task)})
        results = []
        for genome, per_task in zip(genomes, details):
            mse = float(np.mean([r["query_mse"] for r in per_task]))
            results.append({"fitness": -mse, "descriptor": [mse], "constraints": True,
                            "metrics": {"query_mse": mse, "gradient_steps": steps*len(per_task),
                                        "learned_weights": genome.tolist(), "per_task": per_task,
                                        "train_task_ids": self.train_task_ids,
                                        "selection_split": "training_tasks_query_sets"}})
        return results

    def replay(self, seed: int = 10000) -> dict[str, Any]:
        if self.best_genome is None:
            raise ValueError("run at least one generation before replay")
        task_rng = np.random.default_rng(seed)
        details = []
        steps = 0 if self.inheritance == "none" else self.inner_steps
        seen = set(self.train_tasks)
        for i in range(6):
            task = (float(task_rng.uniform(.5, 1.5)), float(task_rng.uniform(-1., 1.)))
            while task in seen:
                task = (float(task_rng.uniform(.5, 1.5)), float(task_rng.uniform(-1., 1.)))
            seen.add(task)
            _, metrics = refine_sine(self.best_genome, self.hidden, task, seed + 2000 + 2*i,
                                     seed + 2001 + 2*i, steps, self.lr, self.device)
            metrics["task_parameters"] = list(task)
            details.append(metrics)
        mse = float(np.mean([d["query_mse"] for d in details]))
        return {"fitness": -mse, "descriptor": [mse], "constraints": True,
                "metrics": {"split": "unseen_tasks", "seed": seed, "per_task": details,
                "train_task_ids": self.train_task_ids, "test_task_ids": [f"test:{seed}:{i}" for i in range(6)],
                "replay_kind": "new_task_adaptation_from_selected_initialization",
                "gradient_steps_during_replay": 6*steps,
                "mean_before_adaptation": float(np.mean([m["initial_query_mse"] for m in details])),
                "mean_after_adaptation": mse}}


def plastic_genome_size(cues: int) -> int:
    return 7 * cues + 3


def plastic_episode(genome: np.ndarray, cues: int, seed: int, plastic: bool = True,
                    device: str | torch.device = "cpu") -> dict[str, Any]:
    """Evolved ABCD local rules, rates, and a feedback-sensitive neuromodulator.

    During support, a teacher clamps postsynaptic activity to the observed target.
    During queries, the neuron supplies its own activity and no target feedback.
    Every step can update weights. The genome never receives acquired weights.
    """
    if len(genome) != plastic_genome_size(cues):
        raise ValueError("wrong plastic genome size")
    z = torch.tensor(genome, dtype=torch.float32, device=device)
    weights = z[:cues].clone()
    initial = weights.clone()
    rules = z[cues:5*cues].reshape(4, cues)
    eta = .5 * torch.sigmoid(z[5*cues:6*cues])
    mod_weights = z[6*cues:-1]
    mod_bias = z[-1]
    rng = np.random.default_rng(seed)
    targets = torch.tensor(rng.choice([-1., 1.], cues), dtype=torch.float32, device=device)
    order = [(int(i), True) for _ in range(3) for i in rng.permutation(cues)]
    order += [(int(i), False) for i in rng.permutation(cues)]
    query_errors, modulation, updates = [], [], []
    for cue, feedback_available in order:
        pre = torch.nn.functional.one_hot(torch.tensor(cue, device=device), cues).float()
        prediction = torch.tanh(weights @ pre)
        post = targets[cue] if feedback_available else prediction
        feedback = torch.tensor(float(feedback_available), device=device)
        mod_input = torch.cat([pre, post.reshape(1), feedback.reshape(1)])
        gate = torch.sigmoid(mod_weights @ mod_input + mod_bias)
        a, b, c, d = rules
        delta = eta * gate * (a * pre * post + b * pre + c * post + d)
        if not feedback_available:
            query_errors.append(float((prediction - targets[cue])**2))
        if plastic:
            weights = torch.clamp(weights + delta, -4., 4.)
        modulation.append(float(gate))
        updates.append(float(torch.linalg.vector_norm(delta)) if plastic else 0.)
    return {"mse": float(np.mean(query_errors)), "final_weights": weights.cpu().numpy().tolist(),
            "initial_weights": initial.cpu().numpy().tolist(), "weight_delta": float(torch.linalg.vector_norm(weights-initial)),
            "modulation_min": min(modulation), "modulation_max": max(modulation),
            "modulation": modulation, "weight_updates": updates, "targets": targets.cpu().numpy().tolist()}


class EvolvedPlasticity(Engine):
    method = "evolved_plasticity"
    target = "associative_memory"

    def __init__(self, spec: dict[str, Any]):
        super().__init__(spec)
        self.cues = int(self.parameters.get("cues", 3))
        self.episodes = int(self.parameters.get("episodes", 4))
        if self.cues < 2 or self.episodes < 1:
            raise ValueError("cues >= 2 and episodes >= 1 required")
        self.population = self.rng.normal(0, .4, (self.population_size, plastic_genome_size(self.cues))).astype(np.float32)
        self.population[:, :self.cues] *= .2
        self.lifetime_updates = 0
        self.episode_interactions = 0

    def _result(self, genome: np.ndarray, seeds: list[int]) -> dict[str, Any]:
        enabled = bool(self.parameters.get("plasticity_enabled", True))
        traces = [plastic_episode(genome, self.cues, s, enabled, self.device) for s in seeds]
        frozen = [plastic_episode(genome, self.cues, s, False, self.device)["mse"] for s in seeds]
        mse = float(np.mean([t["mse"] for t in traces]))
        delta = float(np.mean([t["weight_delta"] for t in traces]))
        return {"fitness": -mse, "descriptor": [delta], "constraints": True,
                "metrics": {"query_mse": mse, "frozen_mse": float(np.mean(frozen)),
                "weight_delta": delta, "traces": traces, "episode_seeds": seeds,
                "evolved_fields": ["initial_weights", "A", "B", "C", "D", "eta", "neuromodulator"],
                "teacher_clamping": "support_only", "inheritance": "genotype_only", "plasticity_enabled": enabled}}

    def step(self, ctx: Any) -> None:
        if self.done:
            return
        scores = []
        seeds = [self.seed + 3000 + i for i in range(self.episodes)]
        for i, genome in enumerate(self.population):
            result = ctx.evaluate({"kind": "plastic_neural_rule", "genes": genome.tolist(), "cues": self.cues},
                                  lambda g=genome: self._result(g, seeds), label=f"plasticity/{self.generation}/{i}")
            self._remember(genome, result)
            scores.append(result["fitness"])
            interactions = self.episodes*self.cues*4
            self.episode_interactions += 2*interactions  # learned and frozen counterfactual rollouts
            if self.parameters.get("plasticity_enabled", True):
                self.lifetime_updates += interactions
            ctx.record({"event": "lifetime_plasticity", "candidate": i,
                        "weight_delta": result["metrics"]["weight_delta"],
                        "episodes": self.episodes, "synapse_rule": "ABCD",
                        "neuromodulation": bool(self.parameters.get("plasticity_enabled", True)),
                        "acquired_weights_inherited": False})
        self.population = self._offspring(self.population, scores, float(self.parameters.get("mutation_sigma", .15)),ctx=ctx)
        self._finish(best_fitness=max(scores), episodes=self.episodes)

    def summary(self) -> dict[str, Any]:
        return {**super().summary(), "episode_interactions": self.episode_interactions,
                "lifetime_updates": self.lifetime_updates,
                "plasticity_enabled": bool(self.parameters.get("plasticity_enabled", True))}

    def replay(self, seed: int = 10000) -> dict[str, Any]:
        if self.best_genome is None:
            raise ValueError("run at least one generation before replay")
        result = self._result(self.best_genome, [seed + i for i in range(8)])
        result["metrics"]["split"] = "fresh_association_episodes"
        result["metrics"]["association_overlap_possible"] = True
        result["metrics"]["unseen_association_claim"] = False
        result["metrics"]["replay_kind"] = "lifetime_learning_from_frozen_rule_genotype"
        result["metrics"]["episode_interactions"] = 2*8*self.cues*4
        return result


def control_rollout(actor: nn.Module, seed: int, horizon: int, noise: float = 0.) -> tuple[float, list[tuple], float]:
    rng = np.random.default_rng(seed)
    position, velocity, target = float(rng.uniform(-.5, .5)), 0., float(rng.uniform(-.8, .8))
    transitions, total, actions = [], 0., []
    for t in range(horizon):
        state = np.array([position, velocity, target], dtype=np.float32)
        with torch.no_grad():
            action = float(actor(torch.tensor(state, device=next(actor.parameters()).device))[0])
        action = float(np.clip(action + rng.normal(0, noise), -1., 1.))
        velocity = .6 * velocity + .15 * action
        position = float(np.clip(position + velocity, -2., 2.))
        reward = -(position-target)**2 - .01 * action**2
        following = np.array([position, velocity, target], dtype=np.float32)
        transitions.append((state, np.array([action], dtype=np.float32), reward, following, t == horizon-1))
        total += reward
        actions.append(action)
    return total / horizon, transitions, float(np.mean(actions))


class ERL(Engine):
    method = "erl"
    target = "tracking_control"

    def __init__(self, spec: dict[str, Any]):
        super().__init__(spec)
        self.hidden = int(self.parameters.get("hidden", 8))
        self.horizon = int(self.parameters.get("horizon", 20))
        self.batch_size = int(self.learning.get("batch_size", 16))
        self.inner_steps = int(self.learning.get("inner_steps", 5))
        self.mode = self.parameters.get("mode", "hybrid")
        if self.mode not in {"hybrid", "evolution_only", "learning_only"}:
            raise ValueError("ERL mode must be hybrid, evolution_only, or learning_only")
        if self.horizon < 2 or self.batch_size < 2 or self.inner_steps < 1:
            raise ValueError("ERL requires horizon >= 2, batch_size >= 2, inner_steps >= 1")
        self.actor = make_mlp(3, self.hidden, 1, self.seed, True, device=self.device)
        self.critic = make_mlp(4, 16, 1, self.seed + 991, device=self.device)
        self.target_actor, self.target_critic = copy.deepcopy(self.actor), copy.deepcopy(self.critic)
        self.actor_optimizer = torch.optim.Adam(self.actor.parameters(), lr=float(self.learning.get("learning_rate", .003)))
        self.critic_optimizer = torch.optim.Adam(self.critic.parameters(), lr=.005)
        self.population = np.stack([vector(make_mlp(3, self.hidden, 1, self.seed + i + 1, True))
                                    for i in range(self.population_size)])
        self.replay_buffer: list[tuple] = []
        self.replay_sources = {"population": 0, "rl_actor": 0}
        self.gradient_updates = 0
        self.reinsertions = 0
        self.last_reinserted: np.ndarray | None = None

    def _collect(self, weights: np.ndarray, rollout_seed: int, source: str, noise: float = 0.) -> dict[str, Any]:
        actor = make_mlp(3, self.hidden, 1, 0, True, device=self.device)
        load_vector(actor, weights)
        score, transitions, behavior = control_rollout(actor, rollout_seed, self.horizon, noise)
        return {"fitness": score, "descriptor": [behavior], "constraints": True,
                "metrics": {"mean_reward": score, "transitions": len(transitions), "source": source,
                            "rollout_seed": rollout_seed,
                            "trajectory": [[s.tolist(), a.tolist(), r, n.tolist(), d]
                                           for s, a, r, n, d in transitions]}}

    def _append_trajectory(self, result: dict[str, Any]) -> None:
        # State changes occur after ctx.evaluate, so cached measurements also
        # reconstruct the replay buffer when resuming a partially done generation.
        metrics = result["metrics"]
        transitions = [(np.asarray(s, dtype=np.float32), np.asarray(a, dtype=np.float32),
                        float(r), np.asarray(n, dtype=np.float32), bool(d))
                       for s, a, r, n, d in metrics["trajectory"]]
        self.replay_buffer.extend(transitions)
        self.replay_buffer = self.replay_buffer[-4000:]
        self.replay_sources[metrics["source"]] += len(transitions)

    def _learn(self) -> dict[str, float]:
        before = vector(self.actor)
        losses = []
        if len(self.replay_buffer) < self.batch_size:
            return {"actor_delta": 0., "critic_loss": 0., "updates": 0}
        for _ in range(self.inner_steps):
            indices = self.rng.integers(0, len(self.replay_buffer), self.batch_size)
            items = [self.replay_buffer[i] for i in indices]
            states = torch.tensor(np.stack([a[0] for a in items]), device=self.device)
            actions = torch.tensor(np.stack([a[1] for a in items]), device=self.device)
            rewards = torch.tensor([a[2] for a in items], dtype=torch.float32, device=self.device).unsqueeze(1)
            next_states = torch.tensor(np.stack([a[3] for a in items]), device=self.device)
            dones = torch.tensor([a[4] for a in items], dtype=torch.float32, device=self.device).unsqueeze(1)
            with torch.no_grad():
                targets = rewards + .95*(1.-dones)*self.target_critic(torch.cat([next_states, self.target_actor(next_states)], 1))
            self.critic_optimizer.zero_grad()
            loss = nn.functional.mse_loss(self.critic(torch.cat([states, actions], 1)), targets)
            loss.backward()
            nn.utils.clip_grad_norm_(self.critic.parameters(), 10.)
            self.critic_optimizer.step()
            self.actor_optimizer.zero_grad()
            for p in self.critic.parameters():
                p.requires_grad_(False)
            actor_loss = -self.critic(torch.cat([states, self.actor(states)], 1)).mean()
            actor_loss.backward()
            self.actor_optimizer.step()
            for p in self.critic.parameters():
                p.requires_grad_(True)
            with torch.no_grad():
                for target, live in zip(self.target_actor.parameters(), self.actor.parameters()):
                    target.lerp_(live, .05)
                for target, live in zip(self.target_critic.parameters(), self.critic.parameters()):
                    target.lerp_(live, .05)
            self.gradient_updates += 1
            losses.append(float(loss.detach()))
        return {"actor_delta": float(np.linalg.norm(vector(self.actor)-before)),
                "critic_loss": float(np.mean(losses)), "updates": len(losses)}

    def step(self, ctx: Any) -> None:
        if self.done:
            return
        if self.mode == "learning_only":
            self._step_learning_only(ctx)
            return
        scores = []
        for i, genome in enumerate(self.population):
            rs = self.seed + 5000 + self.generation*100 + i
            result = ctx.evaluate({"kind": "neural_policy", "weights": genome.tolist(), "rollout_seed": rs},
                lambda g=genome, s=rs: self._collect(g, s, "population"), label=f"erl/{self.generation}/{i}")
            self._append_trajectory(result)
            scores.append(result["fitness"])
            self._remember(genome, result)
        if self.mode == "hybrid":
            rs = self.seed + 5000 + self.generation*100 + self.population_size
            rl_weights = vector(self.actor)
            rl_result = ctx.evaluate({"kind": "rl_exploration_policy", "weights": rl_weights.tolist(), "rollout_seed": rs},
                         lambda: self._collect(rl_weights, rs, "rl_actor", .15), label=f"erl/rl_actor/{self.generation}")
            self._append_trajectory(rl_result)
            updates = self._learn()
        else:
            updates = {"actor_delta": 0., "critic_loss": 0., "updates": 0}
        self.population = self._offspring(self.population, scores, float(self.parameters.get("mutation_sigma", .06)),ctx=ctx)
        reinsertion = self.mode == "hybrid" and self.parameters.get("rl_reinsertion", True)
        if reinsertion:
            self.last_reinserted = vector(self.actor)
            self.population[-1] = self.last_reinserted.copy()
            self.reinsertions += 1
        ctx.record({"event": "erl_shared_replay_and_reinsertion" if self.mode == "hybrid" else "evolution_only_control",
                    "mode": self.mode, "buffer_size": len(self.replay_buffer),
                    "sources": self.replay_sources.copy(), "gradient_updates": updates["updates"],
                    "actor_delta": updates["actor_delta"],
                    "reinsertion_slot": self.population_size-1 if reinsertion else None,
                    "reinserted_hash": tensor_digest(self.last_reinserted) if self.last_reinserted is not None else None,
                    "algorithm": "DDPG" if self.mode == "hybrid" else "population GA"})
        self._finish(best_fitness=max(scores), replay_size=len(self.replay_buffer), **updates)

    def _step_learning_only(self, ctx: Any) -> None:
        scores = []
        weights = vector(self.actor)
        for i in range(self.population_size):
            rs = self.seed + 5000 + self.generation*100 + i
            result = ctx.evaluate({"kind": "ddpg_exploration_policy", "weights": weights.tolist(), "rollout_seed": rs},
                        lambda s=rs: self._collect(weights, s, "rl_actor", .15),
                        label=f"erl/learning_only/{self.generation}/{i}")
            self._append_trajectory(result)
            scores.append(result["fitness"])
        updates = self._learn()
        # The learning-only control returns its final trained actor, with no
        # evolutionary best-of-population selection. Its post-update training
        # fitness has not been measured, so never attach the pre-update score.
        self.best_genome = vector(self.actor)
        self.best_fitness = None
        ctx.record({"event": "learning_only_control", "algorithm": "DDPG", "mode": self.mode,
                    "sources": self.replay_sources.copy(), "gradient_updates": updates["updates"],
                    "actor_delta": updates["actor_delta"], "trained_actor_hash": tensor_digest(self.best_genome),
                    "selection": "final_gradient_actor", "evolutionary_selection": False})
        self._finish(mean_pre_update_exploration_reward=float(np.mean(scores)),
                     replay_size=len(self.replay_buffer), **updates)

    def summary(self) -> dict[str, Any]:
        descriptions = {"hybrid": "ERL with DDPG actor/critic, replay, target networks, and actor reinsertion",
                        "evolution_only": "population GA control; no gradient updates or RL actor trajectories",
                        "learning_only": "DDPG control; no evolutionary selection or actor reinsertion"}
        if self.mode == "hybrid" and not self.parameters.get("rl_reinsertion", True):
            descriptions["hybrid"] = "ERL ablation without learned-actor reinsertion"
        return {**super().summary(), "mode": self.mode,
                "replay_size": len(self.replay_buffer), "replay_sources": self.replay_sources,
                "gradient_updates": self.gradient_updates, "reinsertions": self.reinsertions,
                "actor_optimizer_steps": self.gradient_updates, "critic_optimizer_steps": self.gradient_updates,
                "environment_interactions": sum(self.replay_sources.values()),
                "algorithm": descriptions[self.mode],
                "policy_selection": "final_gradient_actor" if self.mode == "learning_only" else "best_observed_population_policy"}

    def replay(self, seed: int = 10000) -> dict[str, Any]:
        if self.best_genome is None:
            raise ValueError("run at least one generation before replay")
        actor = make_mlp(3, self.hidden, 1, 0, True, device=self.device)
        load_vector(actor, self.best_genome)
        scores = [control_rollout(actor, seed+i, self.horizon)[0] for i in range(8)]
        rollouts_per_generation = self.population_size + int(self.mode == "hybrid")
        training_seeds = {self.seed+5000+g*100+i for g in range(self.generation) for i in range(rollouts_per_generation)}
        overlap = len(training_seeds & set(range(seed, seed+8)))
        return {"fitness": float(np.mean(scores)), "descriptor": [float(np.std(scores))], "constraints": True,
                "metrics": {"split": "heldout_rollouts" if not overlap else "includes_training_seeds",
                            "training_seed_overlap": overlap, "seed": seed, "episode_rewards": scores,
                            "gradient_updates_during_replay": 0, "environment_interactions": 8*self.horizon,
                            "replay_kind": "frozen_selected_policy"}}


def arm_values_and_jacobian(angles: np.ndarray, device: str | torch.device = "cpu") -> tuple[np.ndarray, np.ndarray]:
    dtype = torch.float32 if torch.device(device).type == "mps" else torch.float64
    theta = torch.tensor(angles, dtype=dtype, requires_grad=True, device=device)
    def values(x: torch.Tensor) -> torch.Tensor:
        cumulative = x.cumsum(0)
        return torch.stack([-((x-x.mean())**2).mean(), cumulative.cos().mean(), cumulative.sin().mean()])
    out = values(theta)
    jacobian = torch.autograd.functional.jacobian(values, theta)
    return out.detach().cpu().numpy(), jacobian.detach().cpu().numpy()


class DifferentiableQD(Engine):
    method = "differentiable_qd"
    target = "differentiable_arm"

    def __init__(self, spec: dict[str, Any]):
        super().__init__(spec)
        self.dimensions = int(self.parameters.get("joints", 4))
        self.bins = int(self.parameters.get("bins", 8))
        self.step_size = float(self.parameters.get("step_size", .35))
        if self.dimensions < 2 or self.bins < 2 or self.step_size <= 0:
            raise ValueError("joints >= 2, bins >= 2 and step_size > 0 required")
        self.archive: dict[tuple[int, int], tuple[float, np.ndarray]] = {}
        self.jacobian_evaluations = 0
        self.last_jacobian: np.ndarray | None = None

    def cell(self, descriptor: list[float]) -> tuple[int, int]:
        a = np.clip(np.floor((np.asarray(descriptor)+1.)*.5*self.bins).astype(int), 0, self.bins-1)
        return int(a[0]), int(a[1])

    def _measurement(self, angles: np.ndarray) -> dict[str, Any]:
        dtype = torch.float32 if self.device.type == "mps" else torch.float64
        x = torch.tensor(angles, dtype=dtype, device=self.device)
        cumulative = x.cumsum(0)
        values = torch.stack([-((x-x.mean())**2).mean(), cumulative.cos().mean(), cumulative.sin().mean()]).cpu().numpy()
        return {"fitness": float(values[0]), "descriptor": values[1:].tolist(), "constraints": True,
                "metrics": {"angle_variance": -float(values[0]), "end_effector": values[1:].tolist()}}

    def step(self, ctx: Any) -> None:
        if self.done:
            return
        for i in range(self.population_size):
            if not self.parameters.get("gradient_proposals", True) or not self.archive or self.rng.random() < .2:
                candidate = self.rng.uniform(-math.pi, math.pi, self.dimensions)
                origin = "random_restart"
            else:
                entries = list(self.archive.values())
                parent = entries[int(self.rng.integers(len(entries)))][1]
                _, jac = arm_values_and_jacobian(parent, self.device)
                self.last_jacobian = jac.copy()
                self.jacobian_evaluations += 1
                normalized = jac / np.maximum(np.linalg.norm(jac, axis=1, keepdims=True), 1e-12)
                coefficients = np.r_[1., self.rng.normal(0, 2., 2)]
                candidate = parent + self.step_size*(coefficients @ normalized)
                candidate = (candidate + math.pi) % (2*math.pi) - math.pi
                origin = "objective_and_descriptor_gradient"
                ctx.record({"event": "dqd_jacobian", "parent_hash": tensor_digest(parent),
                            "jacobian_shape": list(jac.shape), "jacobian": jac.tolist(),
                            "coefficients": coefficients.tolist(), "proposal_hash": tensor_digest(candidate)})
            result = ctx.evaluate({"kind": "arm_angles", "angles": candidate.tolist()},
                                  lambda g=candidate: self._measurement(g), label=f"dqd/{self.generation}/{i}")
            key = self.cell(result["descriptor"])
            replaced = key not in self.archive or result["fitness"] > self.archive[key][0]
            if replaced:
                self.archive[key] = (result["fitness"], candidate.copy())
            self._remember(candidate, result)
            ctx.record({"event": "dqd_archive", "cell": list(key), "replaced": replaced,
                        "origin": origin, "occupied_cells": len(self.archive)})
        self._finish(occupied_cells=len(self.archive), coverage=len(self.archive)/self.bins**2,
                     jacobian_evaluations=self.jacobian_evaluations)

    def summary(self) -> dict[str, Any]:
        algorithm = "normalized-gradient MAP-Elites variant" if self.parameters.get("gradient_proposals", True) else "random-proposal MAP-Elites control"
        return {**super().summary(), "algorithm": algorithm,
                "gradient_dtype": "float32" if self.device.type == "mps" else "float64",
                "not_implemented": "CMA-MEGA / CMA-MAEGA adaptive coefficient emitter",
                "occupied_cells": len(self.archive), "coverage": len(self.archive)/self.bins**2,
                "jacobian_evaluations": self.jacobian_evaluations}

    def replay(self, seed: int = 10000) -> dict[str, Any]:
        if self.best_genome is None:
            raise ValueError("run at least one generation before replay")
        consistent = all(self.cell(self._measurement(g)["descriptor"]) == cell and
                         abs(self._measurement(g)["fitness"]-score) < 1e-10
                         for cell, (score, g) in self.archive.items())
        result = self._measurement(self.best_genome)
        result["metrics"].update({"archive_recomputed": True, "archive_consistent": consistent,
                                  "occupied_cells": len(self.archive), "seed": seed})
        return result


METHODS = {"gradient_refinement": GradientRefinement, "evolutionary_initialization": EvolutionaryInitialization,
           "evolved_plasticity": EvolvedPlasticity, "erl": ERL, "differentiable_qd": DifferentiableQD}
