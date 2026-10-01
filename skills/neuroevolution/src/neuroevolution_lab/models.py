"""Evolution over actual tiny autoregressive LM tensors on explicit devices.

These experiments train local models on synthetic arithmetic token sequences.
They do not adapt hosted LLM weights or reproduce large-model benchmark results.
The reference path uses individual nn.GRU calls; the tensor path evaluates
population batches with equivalent GRU equations and persistent device sources.
"""
from __future__ import annotations

import copy
import hashlib
from typing import Any

import numpy as np
import torch
from torch import nn

from .learning import Engine, load_vector, tensor_digest, vector


VOCABULARY = 12  # digits 0..9 and explicit addition/subtraction task markers 10/11


class TinyAutoregressiveLM(nn.Module):
    def __init__(self, hidden: int = 12, seed: int = 0, device: str | torch.device = "cpu"):
        super().__init__()
        with torch.random.fork_rng():
            torch.manual_seed(seed)
            self.embedding = nn.Embedding(VOCABULARY, hidden)
            self.recurrent = nn.GRU(hidden, hidden, batch_first=True)
            self.output = nn.Linear(hidden, VOCABULARY)
        self.to(device)

    def forward(self, tokens: torch.Tensor) -> torch.Tensor:
        hidden, _ = self.recurrent(self.embedding(tokens))
        return self.output(hidden)


def arithmetic_sequences(seed: int, length: int = 9) -> dict[str, torch.Tensor]:
    """Partition unique (operation, start, stride) tasks before making sequences.

    Each domain has 40 unique tasks: train 24, validation 8, test 8. Consequently
    both exact sequences and task identifiers are disjoint between splits.
    """
    if length < 5:
        raise ValueError("sequence length must be >= 5")
    rng = np.random.default_rng(seed)
    result: dict[str, list[list[int]]] = {name: [] for name in ("train", "validation", "test")}
    for operation in range(2):
        tasks = [(start, stride) for start in range(10) for stride in range(1, 5)]
        order = rng.permutation(len(tasks))
        for index, task_index in enumerate(order):
            start, stride = tasks[task_index]
            sequence = [10 + operation, start, stride]
            value = start
            while len(sequence) < length:
                value = (value + stride*(1 if operation == 0 else -1)) % 10
                sequence.append(value)
            split = "train" if index < 24 else "validation" if index < 32 else "test"
            result[split].append(sequence)
    return {k: torch.tensor(v, dtype=torch.long) for k, v in result.items()}


def state_digest(state: dict[str, torch.Tensor]) -> str:
    digest = hashlib.sha256()
    for name, tensor in sorted(state.items()):
        digest.update(name.encode())
        digest.update(str(tuple(tensor.shape)).encode())
        digest.update(tensor.detach().cpu().numpy().tobytes())
    return digest.hexdigest()


def validate_aligned_states(states: list[dict[str, torch.Tensor]]) -> None:
    if len(states) != 2:
        raise ValueError("reference merging supports exactly two aligned source models")
    first = states[0]
    if set(first) != set(states[1]):
        raise ValueError("source model state names do not align")
    for name, tensor in first.items():
        other = states[1][name]
        if tensor.shape != other.shape or tensor.dtype != other.dtype:
            raise ValueError(f"unaligned tensor shape or dtype: {name}")
        if not tensor.is_floating_point() or not torch.isfinite(tensor).all() or not torch.isfinite(other).all():
            raise ValueError(f"finite floating-point tensors required: {name}")


def merge_states(states: list[dict[str, torch.Tensor]], coefficients: np.ndarray) -> dict[str, torch.Tensor]:
    """Merge embedding, recurrent, and output tensors using explicit coefficients.

    Architecture alignment is checked here; engines also ensure the source models
    descend from an identical initialization. No permutation alignment is claimed.
    """
    validate_aligned_states(states)
    coefficients = np.asarray(coefficients)
    if coefficients.shape != (3,) or not np.isfinite(coefficients).all() or (coefficients < 0).any() or (coefficients > 1).any():
        raise ValueError("three finite convex merge coefficients in [0, 1] required")
    result = {}
    for name in states[0]:
        group = 0 if name.startswith("embedding.") else 1 if name.startswith("recurrent.") else 2
        alpha = float(coefficients[group])
        result[name] = (1.-alpha)*states[0][name] + alpha*states[1][name]
    return result


def next_token_loss(model: TinyAutoregressiveLM, data: torch.Tensor) -> torch.Tensor:
    predictions = model(data[:, :-1])
    return nn.functional.cross_entropy(predictions.reshape(-1, VOCABULARY), data[:, 1:].reshape(-1))


def train_model(model: TinyAutoregressiveLM, data: torch.Tensor, steps: int, lr: float) -> dict[str, float]:
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    before = vector(model)
    with torch.no_grad():
        initial_loss = float(next_token_loss(model, data))
    model.train()
    for _ in range(steps):
        optimizer.zero_grad()
        loss = next_token_loss(model, data)
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), 5.)
        optimizer.step()
    model.eval()
    with torch.no_grad():
        final_loss = float(next_token_loss(model, data))
    return {"steps": steps, "training_sequences": len(data), "initial_train_loss": initial_loss,
            "final_train_loss": final_loss, "tensor_delta_l2": float(np.linalg.norm(vector(model)-before))}


def evaluate_state(state: dict[str, torch.Tensor], hidden: int, data: torch.Tensor) -> dict[str, Any]:
    device = next(iter(state.values())).device
    model = TinyAutoregressiveLM(hidden, device=device)
    model.load_state_dict(state)
    data = data.to(device)
    model.eval()
    with torch.no_grad():
        loss = float(next_token_loss(model, data))
        domains = [float(next_token_loss(model, data[data[:, 0] == marker])) for marker in (10, 11)]
        logits = model(data[:, :-1])
        accuracy = float((logits.argmax(-1) == data[:, 1:]).float().mean())
    return {"fitness": -loss, "descriptor": domains, "constraints": True,
            "metrics": {"next_token_loss": loss, "token_accuracy": accuracy,
                        "domain_losses": domains, "tensor_hash": state_digest(state),
                        "sequence_count": len(data), "vocabulary_size": VOCABULARY,
                        "teacher_forced_tokens": len(data)*(data.shape[1]-1)}}


class ModelMerging(Engine):
    method = "model_merging"
    target = "tiny_autoregressive"

    def __init__(self, spec: dict[str, Any]):
        super().__init__(spec)
        self.hidden = int(self.parameters.get("hidden", 12))
        self.train_steps = int(self.learning.get("inner_steps", 30))
        self.lr = float(self.learning.get("learning_rate", .015))
        if self.hidden < 2 or self.train_steps < 1 or self.lr <= 0:
            raise ValueError("hidden >= 2, inner_steps >= 1 and learning_rate > 0 required")
        self.data = {name: value.to(self.device) for name, value in arithmetic_sequences(self.seed + 100).items()}
        self.initial_state = copy.deepcopy(TinyAutoregressiveLM(self.hidden, self.seed, device=self.device).state_dict())
        self.initial_hash = state_digest(self.initial_state)
        self.sources: list[dict[str, torch.Tensor]] = []
        self.training_records: list[dict[str, Any]] = []
        self.population = self.rng.uniform(0., 1., (self.population_size, 3)).astype(np.float32)
        self.population[0] = .5
        self.prepared = False

    def _prepare(self, ctx: Any) -> None:
        if self.prepared:
            return
        for domain, marker in enumerate((10, 11)):
            model = TinyAutoregressiveLM(self.hidden, device=self.device)
            model.load_state_dict(self.initial_state)
            training = self.data["train"][self.data["train"][:, 0] == marker]
            record = train_model(model, training, self.train_steps, self.lr)
            self.sources.append(copy.deepcopy(model.state_dict()))
            event = {"event": "source_lm_training", "domain": domain, "shared_initialization": self.initial_hash,
                     "source_tensor_hash": state_digest(self.sources[-1]), "split": "train", **record}
            self.training_records.append(event)
            ctx.record(event)
        self.prepared = True

    def _state(self, genome: np.ndarray) -> dict[str, torch.Tensor]:
        return merge_states(self.sources, genome)

    def _batch_states(self, genomes: np.ndarray) -> dict[str, torch.Tensor]:
        validate_aligned_states(self.sources)
        if genomes.ndim != 2 or genomes.shape[1] != 3 or not np.isfinite(genomes).all() or (genomes < 0).any() or (genomes > 1).any():
            raise ValueError("three finite convex merge coefficients per candidate required")
        coefficients = torch.tensor(genomes, dtype=torch.float32, device=self.device)
        merged = {}
        for name, source in self.sources[0].items():
            group = 0 if name.startswith("embedding.") else 1 if name.startswith("recurrent.") else 2
            alpha = coefficients[:, group].reshape(-1, *([1]*source.ndim))
            merged[name] = (1.-alpha)*source[None] + alpha*self.sources[1][name][None]
        return merged

    def _batch_results(self, indices: list[int]) -> list[dict]:
        from .accelerator_learning import lm_population_results
        return lm_population_results(self._batch_states(self.population[indices]), self.data["validation"])

    def step(self, ctx: Any) -> None:
        if self.done:
            return
        self._prepare(ctx)
        scores = []
        source_ids = [state_digest(source) for source in self.sources]
        records = [{"kind": "aligned_tensor_merge", "coefficients": genome.tolist(), "source_hashes": source_ids}
                   for genome in self.population]
        labels = [f"model_merge/{self.generation}/{i}" for i in range(len(records))]
        single = lambda i: evaluate_state(self._state(self.population[i]), self.hidden, self.data["validation"])
        for i, result in self._population_evaluations(ctx, records, single, self._batch_results, labels):
            genome = self.population[i]
            scores.append(result["fitness"])
            self._remember(genome, result)
            ctx.record({"event": "aligned_tensor_merge", "coefficients": genome.tolist(),
                        "source_hashes": source_ids, "output_tensor_hash": result["metrics"]["tensor_hash"],
                        "selection_split": "validation", "shared_initialization": self.initial_hash,
                        "groups": ["embedding", "recurrent", "output"]})
        self.population = np.clip(self._offspring(self.population, scores,
                                  float(self.parameters.get("mutation_sigma", .12)),ctx=ctx), 0., 1.)
        ctx.record({"event":"merge_coefficient_projection","generation":self.generation+1,
                    "projection":"clip [0,1]","child_hashes":[tensor_digest(g) for g in self.population]})
        self._finish(best_fitness=max(scores), source_models=len(self.sources))

    def summary(self) -> dict[str, Any]:
        return {**super().summary(), "architecture": "embedding-GRU-linear autoregressive LM",
                "source_models": len(self.sources), "training": self.training_records,
                "gradient_steps": sum(r["steps"] for r in self.training_records),
                "split_counts": {k: len(v) for k, v in self.data.items()},
                "alignment": "identical architecture and shared initialization; no permutation matching",
                "parameter_access": "local PyTorch tensors", "hosted_model_weights_changed": False}

    def replay(self, seed: int = 10000) -> dict[str, Any]:
        if self.best_genome is None:
            raise ValueError("run at least one generation before replay")
        result = evaluate_state(self._state(self.best_genome), self.hidden, self.data["test"])
        source_losses = [evaluate_state(state, self.hidden, self.data["test"])["metrics"]["next_token_loss"]
                         for state in self.sources]
        result["metrics"].update({"split": "heldout_tasks_and_sequences", "source_test_losses": source_losses,
                                  "coefficients": self.best_genome.tolist(), "seed": seed,
                                  "test_selection": False, "test_set": "fixed predeclared task partition"})
        result["metrics"]["replay_kind"] = "frozen_selected_merged_tensors"
        return result


def adapter_state(base: dict[str, torch.Tensor], genome: np.ndarray, hidden: int, rank: int) -> dict[str, torch.Tensor]:
    if rank < 1 or len(genome) != rank*(hidden+VOCABULARY):
        raise ValueError("wrong low-rank adapter dimensions")
    if not np.isfinite(genome).all():
        raise ValueError("adapter genes must be finite")
    device = base["output.weight"].device
    a = torch.tensor(genome[:rank*hidden].reshape(rank, hidden), dtype=torch.float32, device=device)
    b = torch.tensor(genome[rank*hidden:].reshape(VOCABULARY, rank), dtype=torch.float32, device=device)
    state = copy.deepcopy(base)
    state["output.weight"] = base["output.weight"] + (b @ a)/rank
    return state


class ParameterEvolution(ModelMerging):
    method = "parameter_evolution"

    def __init__(self, spec: dict[str, Any]):
        super().__init__(spec)
        self.mode = self.parameters.get("mode", "adapter")
        if self.mode not in {"adapter", "full"}:
            raise ValueError("parameter mode must be adapter or full")
        self.rank = int(self.parameters.get("rank", 2))
        if self.rank < 1:
            raise ValueError("rank must be positive")
        self.base_state: dict[str, torch.Tensor] | None = None
        if self.mode == "adapter":
            size = self.rank*(self.hidden + VOCABULARY)
            self.population = self.rng.normal(0., .08, (self.population_size, size)).astype(np.float32)
            self.population[0, self.rank*self.hidden:] = 0.
        else:
            # Populated from trained base in _prepare; factory does not run training.
            self.population = np.empty((self.population_size, 0), dtype=np.float32)

    def _prepare(self, ctx: Any) -> None:
        if self.prepared:
            return
        model = TinyAutoregressiveLM(self.hidden, device=self.device)
        model.load_state_dict(self.initial_state)
        record = train_model(model, self.data["train"], self.train_steps, self.lr)
        self.base_state = copy.deepcopy(model.state_dict())
        self.sources = [copy.deepcopy(self.base_state)]
        event = {"event": "base_lm_training", "split": "train", "base_tensor_hash": state_digest(self.base_state),
                 "initialization_hash": self.initial_hash, **record}
        self.training_records.append(event)
        ctx.record(event)
        if self.mode == "full":
            center = vector(model)
            self.population = np.stack([center] + [center + self.rng.normal(0, .01, len(center)).astype(np.float32)
                                                   for _ in range(self.population_size-1)])
        self.prepared = True

    def _state(self, genome: np.ndarray) -> dict[str, torch.Tensor]:
        if self.base_state is None:
            raise ValueError("base model not trained yet")
        if self.mode == "adapter":
            return adapter_state(self.base_state, genome, self.hidden, self.rank)
        model = TinyAutoregressiveLM(self.hidden, device=self.device)
        load_vector(model, genome)
        return copy.deepcopy(model.state_dict())

    def _batch_states(self, genomes: np.ndarray) -> dict[str, torch.Tensor]:
        if self.base_state is None:
            raise ValueError("base model not trained yet")
        if not np.isfinite(genomes).all():
            raise ValueError("finite model parameters required")
        genes = torch.tensor(genomes, dtype=torch.float32, device=self.device)
        population = len(genomes)
        if self.mode == "adapter":
            expected = self.rank*(self.hidden+VOCABULARY)
            if genes.shape != (population, expected):
                raise ValueError("wrong low-rank adapter dimensions")
            states = {name: value[None].expand(population, *value.shape) for name, value in self.base_state.items()}
            a = genes[:, :self.rank*self.hidden].reshape(population, self.rank, self.hidden)
            b = genes[:, self.rank*self.hidden:].reshape(population, VOCABULARY, self.rank)
            states["output.weight"] = self.base_state["output.weight"][None] + torch.bmm(b, a)/self.rank
            return states
        if genes.shape[1] != sum(value.numel() for value in self.base_state.values()):
            raise ValueError("wrong full-model parameter count")
        # TinyAutoregressiveLM registers parameters in state_dict order and has
        # no nonparameter buffers. Keep this explicit to avoid implicit alignment.
        states, offset = {}, 0
        for name, value in self.base_state.items():
            states[name] = genes[:, offset:offset+value.numel()].reshape(population, *value.shape)
            offset += value.numel()
        return states

    def step(self, ctx: Any) -> None:
        if self.done:
            return
        self._prepare(ctx)
        assert self.base_state is not None
        scores = []
        base_hash = state_digest(self.base_state)
        records = [{"kind": "lm_tensor_parameters", "mode": self.mode,
                    "parameters": genome.tolist(), "base_hash": base_hash} for genome in self.population]
        labels = [f"parameter_evolution/{self.generation}/{i}" for i in range(len(records))]
        single = lambda i: evaluate_state(self._state(self.population[i]), self.hidden, self.data["validation"])
        for i, result in self._population_evaluations(ctx, records, single, self._batch_results, labels):
            genome = self.population[i]
            scores.append(result["fitness"])
            self._remember(genome, result)
            ctx.record({"event": "lm_parameter_evaluation", "mode": self.mode,
                        "genome_hash": tensor_digest(genome), "effective_tensor_hash": result["metrics"]["tensor_hash"],
                        "base_hash": base_hash, "selection_split": "validation", "parameter_count": len(genome),
                        "base_frozen": self.mode == "adapter"})
        sigma = float(self.parameters.get("mutation_sigma", .04 if self.mode == "adapter" else .008))
        self.population = self._offspring(self.population, scores, sigma,ctx=ctx)
        self._finish(best_fitness=max(scores), mode=self.mode, evolved_parameters=self.population.shape[1])

    def summary(self) -> dict[str, Any]:
        result = super().summary()
        result.pop("alignment", None)
        result.update({"mode": self.mode, "rank": self.rank if self.mode == "adapter" else None,
                       "base_frozen": self.mode == "adapter", "evolved_parameters": self.population.shape[1],
                       "adapter_target": "output projection" if self.mode == "adapter" else None})
        return result

    def replay(self, seed: int = 10000) -> dict[str, Any]:
        if self.best_genome is None or self.base_state is None:
            raise ValueError("run at least one generation before replay")
        result = evaluate_state(self._state(self.best_genome), self.hidden, self.data["test"])
        result["metrics"].update({"split": "heldout_tasks_and_sequences", "seed": seed,
                                  "mode": self.mode, "base_test_loss": evaluate_state(self.base_state,
                                  self.hidden, self.data["test"])["metrics"]["next_token_loss"],
                                  "test_selection": False, "test_set": "fixed predeclared task partition"})
        result["metrics"]["replay_kind"] = "frozen_selected_model_tensors"
        return result


METHODS = {"model_merging": ModelMerging, "parameter_evolution": ParameterEvolution}
