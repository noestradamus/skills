"""Direct NEAT, CPPNs, fixed-substrate HyperNEAT, and trained modular NAS."""
from __future__ import annotations

import copy
import os
import random
import tempfile

import numpy as np
import neat

from .search import TARGETS, evaluate_controller, evaluate_policy, target_name


def _compute_settings(compute=None):
    settings = {"device": "cpu", "backend": "reference", "batch_size": 32, **(compute or {})}
    if settings["backend"] not in {"reference", "torch"}:
        raise ValueError("Structural evaluation backend must be reference or torch")
    if settings["backend"] == "reference" and settings["device"] != "cpu":
        raise ValueError("The reference structural backend runs on CPU; request backend='torch' for an accelerator")
    if int(settings["batch_size"]) < 1:
        raise ValueError("compute.batch_size must be positive")
    from .devices import resolve_device
    resolve_device(settings)
    return settings


class _DeferredMembers:
    """Transient species view retaining parents throughout interspecies mating."""
    def __init__(self, species):
        object.__setattr__(self, "original", species)
        object.__setattr__(self, "clear_pending", False)

    def __getattr__(self, key):
        return getattr(self.original, key)

    def __setattr__(self, key, value):
        if key == "members" and value == {}:
            object.__setattr__(self, "clear_pending", True)
        else:
            setattr(self.original, key, value)


class CanonicalReproduction(neat.DefaultReproduction):
    """Narrow repair for the pinned upstream's interspecies-parent clearing bug.

    Upstream empties earlier species before later species sample their parents.
    Defer only those clears; preserve upstream selection, sharing and offspring
    allocation, and return the original Species objects before re-speciation.
    """
    def reproduce(self, config, species, pop_size, generation):
        views = {key: _DeferredMembers(value) for key, value in species.species.items()}
        species.species = views.copy()
        try:
            return super().reproduce(config, species, pop_size, generation)
        finally:
            species.species = {key: value.original if isinstance(value, _DeferredMembers) else value
                               for key, value in species.species.items()}
            for view in views.values():
                if view.clear_pending:
                    view.original.members = {}


class CanonicalGenome(neat.DefaultGenome):
    """Correct two pinned-upstream departures from the book's NEAT profile.

    Equation 3.1 averages weight differences over matching genes, independently
    of the larger genome's length used for structural differences. Figure 3.6
    (and the original paper's Figure 4) allows both tied parents' unmatched genes
    to be inherited. Unequal-fitness crossover and innovation creation remain
    upstream operations. CPPN node functions and their defaults are unchanged.
    N is the larger connection count even below 20 genes (the original paper's
    N=1 convention is optional). Disabled genes count; neuron/bias/activation
    differences and enable-state penalties are excluded from this profile.
    """
    def distance(self, other, config):
        if config.compatibility_include_node_genes or config.compatibility_enable_penalty != 0:
            raise ValueError("Canonical NEAT distance excludes node-gene and enable-state penalties")
        distance = super().distance(other, config)
        first = {gene.innovation: gene for gene in self.connections.values()}
        second = {gene.innovation: gene for gene in other.connections.values()}
        matching = [(gene, second[innovation]) for innovation, gene in first.items()
                    if innovation in second and gene.key == second[innovation].key]
        if matching:
            # Upstream divides this weighted sum by N along with E and D.
            # Replace only that divisor; retain its excess/disjoint handling.
            weighted_difference = sum(a.distance(b, config) for a, b in matching)
            distance += weighted_difference * (1 / len(matching) - 1 / max(len(first), len(second)))
        return distance

    def configure_crossover(self, genome1, genome2, config, fitness_criterion=None):
        if genome1.fitness != genome2.fitness:
            return super().configure_crossover(genome1, genome2, config, fitness_criterion)
        from neat.graphs import creates_cycle

        first = {gene.innovation: gene for gene in genome1.connections.values()}
        second = {gene.innovation: gene for gene in genome2.connections.values()}
        inherited = []
        for innovation in sorted(first.keys() | second.keys()):
            a, b = first.get(innovation), second.get(innovation)
            if a is not None and b is not None and a.key == b.key:
                inherited.append(a.crossover(b, disable_rule=config.disable_rule))
            else:
                # Each unmatched gene has an independent half chance, including
                # genes from either tied parent. Innovation numbers never change.
                for gene in (a, b):
                    if gene is not None and random.random() < .5:
                        inherited.append(gene.copy())
        # Two parents can independently evolve the same endpoints with different
        # innovations. Randomize insertion so endpoint/cycle conflicts do not
        # systematically privilege a parent or the lower innovation number.
        random.shuffle(inherited)
        for gene in inherited:
            if gene.key in self.connections:
                continue
            if config.feed_forward and creates_cycle(list(self.connections), gene.key):
                continue
            self.connections[gene.key] = gene

        required = set(config.output_keys)
        required.update(node for edge in self.connections for node in edge
                        if node not in config.input_keys)
        for key in sorted(required):
            a, b = genome1.nodes.get(key), genome2.nodes.get(key)
            if a is not None and b is not None:
                self.nodes[key] = a.crossover(b, disable_rule=config.disable_rule)
            else:
                self.nodes[key] = (a if a is not None else b).copy()


def neat_configuration(n_inputs, n_outputs, size, seed, activation="tanh", cppn=False):
    """Explicit paper-oriented settings on the immutable upstream NEAT adapter.

    This is a documented configuration, not a reproduction of every 2002 setting.
    In particular neuron biases, feed-forward evaluation, and task fitness differ.
    """
    sections = {
        "NEAT": dict(fitness_criterion="max", fitness_threshold=1e20, pop_size=size,
                     reset_on_extinction=True, no_fitness_termination=True, seed=seed),
        "CanonicalGenome": dict(
            num_inputs=n_inputs, num_outputs=n_outputs, num_hidden=0, feed_forward=True,
            initial_connection="full_direct", activation_default=activation,
            activation_mutate_rate=.15 if cppn else 0.,
            activation_options="tanh sin gauss identity sigmoid" if cppn else activation,
            aggregation_default="sum", aggregation_mutate_rate=0., aggregation_options="sum",
            compatibility_disjoint_coefficient=1., compatibility_excess_coefficient="1.0",
            compatibility_weight_coefficient=.4, compatibility_include_node_genes=False,
            compatibility_enable_penalty=0., disable_rule="neat-python",
            conn_add_prob=.25, conn_delete_prob=0., node_add_prob=.2, node_delete_prob=0.,
            single_structural_mutation=False, structural_mutation_surer="default",
            enabled_default=True, enabled_mutate_rate=.01,
            enabled_rate_to_true_add=0., enabled_rate_to_false_add=0.),
        "DefaultSpeciesSet": dict(compatibility_threshold=3., threshold_adjust_rate=.1,
                                  target_num_species=max(2, size//4), threshold_min=.1, threshold_max=100.),
        "DefaultStagnation": dict(species_fitness_func="max", max_stagnation=15, species_elitism=1),
        "CanonicalReproduction": dict(elitism=1, survival_threshold=.3, min_species_size=1,
                                    fitness_sharing="canonical", spawn_method="proportional",
                                    interspecies_crossover_prob=.01),
    }
    genome = sections["CanonicalGenome"]
    for attribute, mean, stdev, rate, power, low, high in [
        ("bias", 0., 1., .7, .5, -10., 10.),
        ("response", 1., 0., 0., 0., .1, 10.),
        ("weight", 0., 1., .8, .5, -10., 10.)]:
        genome.update({f"{attribute}_init_mean": mean, f"{attribute}_init_stdev": stdev,
                       f"{attribute}_init_type": "gaussian", f"{attribute}_max_value": high,
                       f"{attribute}_min_value": low, f"{attribute}_mutate_power": power,
                       f"{attribute}_mutate_rate": rate,
                       f"{attribute}_replace_rate": .1 if rate else 0.})
    return "\n\n".join(f"[{name}]\n" + "\n".join(f"{key} = {value}" for key, value in values.items())
                         for name, values in sections.items()) + "\n"


def serialize_neat(genome):
    return {"key": genome.key,
            "nodes": [{"id": key, "bias": node.bias, "response": node.response,
                       "activation": node.activation, "aggregation": node.aggregation}
                      for key, node in sorted(genome.nodes.items())],
            "connections": [{"source": key[0], "target": key[1], "weight": conn.weight,
                             "enabled": conn.enabled, "innovation": conn.innovation}
                            for key, conn in sorted(genome.connections.items())]}


def substrate_coordinates(width: int, y: float):
    return np.c_[np.linspace(-1, 1, width) if width > 1 else np.array([0.]), np.full(width, y)]


def decode_cppn(cppn, n_inputs, hidden, n_outputs, threshold=.2, weight_scale=3.):
    """Generate two adjacent-layer weight matrices by querying a 5-input CPPN.

    Query: source x/y, destination x/y, Euclidean distance. A distinct coordinate
    supplies each layer's bias input. tanh bounds expression before thresholding.
    No evolved tensor is secretly used as the decoded substrate weights.
    """
    if not 0 <= threshold < 1:
        raise ValueError("CPPN expression threshold must be in [0,1)")
    layers = [substrate_coordinates(n_inputs, -1.), substrate_coordinates(hidden, 0.),
              substrate_coordinates(n_outputs, 1.)]
    matrices = []
    for sources, destinations in zip(layers[:-1], layers[1:]):
        sources = np.vstack([sources, [0., sources[0, 1]-.25]])
        weights = np.zeros((len(sources), len(destinations)))
        for i, source in enumerate(sources):
            for j, destination in enumerate(destinations):
                query = np.r_[source, destination, np.linalg.norm(source-destination)]
                expression = float(np.tanh(cppn.activate(query)[0]))
                weights[i, j] = np.sign(expression)*max(0., abs(expression)-threshold)/(1-threshold)*weight_scale
        matrices.append(weights)
    return np.concatenate([matrix.ravel() for matrix in matrices])


def evaluate_pattern(cppn, resolution=9):
    """Spatial coordinate-to-intensity CPPN; target is a concentric radial pattern."""
    axis = np.linspace(-1, 1, resolution)
    predictions, desired = [], []
    for y in axis:
        for x in axis:
            radius = float(np.hypot(x, y))
            predictions.append(.5 + .5*np.tanh(cppn.activate([x, y, radius, 1.])[0]))
            desired.append(.5 + .5*np.cos(2*np.pi*radius))
    image = np.asarray(predictions).reshape(resolution, resolution)
    mse = float(np.mean((np.asarray(predictions)-desired)**2))
    return {"fitness": 1-mse, "descriptor": [float(image.mean()), float(image.std())],
            "constraints": True, "metrics": {"mse": mse, "resolution": resolution,
                                              "pixels": image.tolist()}}


class StructuralEngine:
    def __init__(self, spec):
        import neat
        self.spec = copy.deepcopy(spec); self.method = spec["method"]
        self.compute = _compute_settings(spec.get("compute"))
        self.parameters = dict(spec.get("parameters", {})); self.seed = int(spec.get("seed", 0))
        self.rng = np.random.default_rng(self.seed)
        self.target = "pattern" if self.method == "cppn" else target_name(spec.get("target", "xor"))
        self.limit = int(spec.get("generations", 10)); self.size = int(spec.get("population_size", 16))
        if self.size < 2 or self.limit < 1:
            raise ValueError("population_size>=2 and generations>=1 are required")
        dimensions = (4, 1) if self.method == "cppn" else (5, 1) if self.method == "hyperneat" else TARGETS[self.target]
        activation = "sigmoid" if self.method == "neat" and self.target == "xor" else "tanh"
        self.config_text = neat_configuration(*dimensions, self.size, self.seed, activation, self.method != "neat")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ini", delete=False) as config_file:
            config_file.write(self.config_text); config_path = config_file.name
        try:
            self.config = neat.Config(CanonicalGenome, CanonicalReproduction,
                                      neat.DefaultSpeciesSet, neat.DefaultStagnation, config_path)
        finally:
            os.unlink(config_path)
        ambient = random.getstate()
        try:
            random.seed(self.seed)
            self.population = neat.Population(self.config)
            self.random_state = random.getstate()
        finally:
            random.setstate(ambient)
        self.generation = 0; self.done = False; self.best = None; self.best_result = None
        self.best_fitness = -float("inf"); self.history = []

    def _evaluate(self, genome, seed):
        compute = _compute_settings(getattr(self, "compute", None))
        if compute["backend"] == "torch":
            from .accelerator_structural import evaluate_structural_batch
            return evaluate_structural_batch([genome], self.config, self.method, self.target,
                                             seed, self.parameters, compute)[0]
        import neat
        network = neat.nn.FeedForwardNetwork.create(genome, self.config)
        if self.method == "cppn":
            return evaluate_pattern(network, int(self.parameters.get("resolution", 9)))
        if self.method == "hyperneat":
            hidden = int(self.parameters.get("hidden", 4)); n_inputs, n_outputs = TARGETS[self.target]
            weights = decode_cppn(network, n_inputs, hidden, n_outputs,
                                  float(self.parameters.get("expression_threshold", .2)),
                                  float(self.parameters.get("weight_scale", 3.)))
            result = evaluate_controller(weights, self.target, seed, self.parameters)
            result["metrics"].update(substrate_parameters=len(weights), expressed_connections=int(np.count_nonzero(weights)),
                                       decoded_weights=weights.tolist())
            return result
        return evaluate_policy(network.activate, self.target, seed, self.parameters)

    def step(self, ctx):
        if self.done:
            return
        evaluated = []

        def evaluate_generation(genomes, _config):
            genomes = list(genomes)
            compute = _compute_settings(getattr(self, "compute", None))
            if compute["backend"] == "torch":
                from .accelerator_structural import evaluate_structural_batch
                results = []
                for start in range(0, len(genomes), int(compute["batch_size"])):
                    chunk = genomes[start:start+int(compute["batch_size"])]
                    encoded = [{"encoding": self.method, "target": self.target, **serialize_neat(genome)}
                               for _, genome in chunk]
                    def measure(indices, current=chunk):
                        return evaluate_structural_batch([current[index][1] for index in indices], self.config,
                                                         self.method, self.target, self.seed, self.parameters, compute)
                    results.extend(ctx.evaluate_batch(encoded, measure,
                                   labels=[f"{self.method}:{self.generation}:{key}" for key, _ in chunk]))
            else:
                results = []
                for key, genome in genomes:
                    encoded = {"encoding": self.method, "target": self.target, **serialize_neat(genome)}
                    results.append(ctx.evaluate(encoded, lambda g=genome: self._evaluate(g, self.seed),
                                               label=f"{self.method}:{self.generation}:{key}"))
            for (key, genome), result in zip(genomes, results):
                genome.fitness = float(result["fitness"]) if result["constraints"] else -1e12
                evaluated.append({"id": key, "fitness": genome.fitness, "nodes": len(genome.nodes),
                                  "connections": len(genome.connections),
                                  "species": self.population.species.genome_to_species[key]})
                if genome.fitness > self.best_fitness:
                    self.best = copy.deepcopy(genome); self.best_fitness = genome.fitness
                    self.best_result = copy.deepcopy(result)
        ambient = random.getstate()
        try:
            random.setstate(self.random_state)
            self.population.run(evaluate_generation, 1)
            self.random_state = random.getstate()
        finally:
            random.setstate(ambient)
        event = {"kind": "structural_generation", "method": self.method, "generation": self.generation,
                 "evaluated": evaluated, "species": len(self.population.species.species),
                 "ancestors": {str(k): list(v) for k, v in self.population.reproduction.ancestors.items()},
                 "best_fitness": self.best_fitness}
        self.history.append({k: v for k, v in event.items() if k != "ancestors"}); ctx.record(event)
        self.generation += 1; self.done = self.generation >= self.limit

    def summary(self):
        canonical_profile = self.config.genome_type is CanonicalGenome
        return {"method": self.method, "target": self.target, "generations": self.generation,
                "best_fitness": self.best_fitness if self.best is not None else None,
                "best_genome": serialize_neat(self.best) if self.best is not None else None,
                "best_result": self.best_result, "history": self.history,
                "configuration": self.config_text,
                "compute": dict(getattr(self, "compute", {"device": "cpu", "backend": "reference", "batch_size": 32})),
                "evolution_backend": "canonical_neat_python" if canonical_profile else "legacy_neat_python",
                "evolution_profile": "paper-profile-v2" if canonical_profile else "legacy",
                "scope": "fixed-substrate HyperNEAT" if self.method == "hyperneat" else self.method}

    def replay(self, seed=None):
        if self.best is None:
            raise ValueError("No evaluated structural genome to replay")
        return self._evaluate(self.best, self.seed if seed is None else int(seed))


def architecture_parameters(architecture):
    widths = [2] + list(architecture["widths"]) + [1]
    return sum((a+1)*b for a, b in zip(widths[:-1], widths[1:]))


def build_torch_model(architecture, seed, device="cpu"):
    import torch
    with torch.random.fork_rng(devices=[]):
        torch.random.default_generator.manual_seed(seed)
        widths = [2] + list(architecture["widths"]) + [1]
        layers = []
        for index, (a, b) in enumerate(zip(widths[:-1], widths[1:])):
            layers.append(torch.nn.Linear(a, b))
            if index < len(widths)-2:
                layers.append(torch.nn.Tanh() if architecture["activations"][index] == "tanh" else torch.nn.ReLU())
        model = torch.nn.Sequential(*layers)
    return model.to(device)


def train_architecture(architecture, seed, steps=60, learning_rate=.05, train_size=64, *, compute=None):
    """Train a genuine modular torch MLP on continuous XOR; score held-out points.

    Initial weights use a private torch generator; torch's ambient RNG is restored.
    Training data and validation data have distinct deterministic seeds.
    """
    import torch
    from .devices import resolve_device, synchronize
    settings = _compute_settings(compute); device = resolve_device(settings)
    model = build_torch_model(architecture, seed, device)
    rng = np.random.default_rng(seed + 1000)
    x_train = rng.uniform(-1, 1, (train_size, 2)).astype("float32")
    y_train = ((x_train[:, 0] >= 0) != (x_train[:, 1] >= 0)).astype("float32")[:, None]
    x_valid = np.random.default_rng(seed+2000).uniform(-1, 1, (128, 2)).astype("float32")
    y_valid = ((x_valid[:, 0] >= 0) != (x_valid[:, 1] >= 0)).astype("float32")[:, None]
    tx, ty = torch.from_numpy(x_train).to(device), torch.from_numpy(y_train).to(device)
    vx, vy = torch.from_numpy(x_valid).to(device), torch.from_numpy(y_valid).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    loss_function = torch.nn.BCEWithLogitsLoss()
    initial = float(loss_function(model(tx), ty).detach())
    for _ in range(steps):
        optimizer.zero_grad(); loss = loss_function(model(tx), ty); loss.backward(); optimizer.step()
    with torch.no_grad():
        valid_loss = float(loss_function(model(vx), vy)); final = float(loss_function(model(tx), ty))
        accuracy = float(((model(vx) >= 0) == vy.bool()).float().mean())
    synchronize(device)
    state = {key: tensor.detach().cpu().tolist() for key, tensor in model.state_dict().items()}
    count = architecture_parameters(architecture)
    result = {"fitness": -valid_loss, "descriptor": [len(architecture["widths"]), count],
            "objectives": [-valid_loss, -float(count)], "constraints": True,
            "metrics": {"initial_training_loss": initial, "final_training_loss": final,
                        "validation_loss": valid_loss, "validation_accuracy": accuracy,
                        "training_steps": steps, "parameters": count, "trained_state": state}}
    if settings["backend"] == "torch":
        result["metrics"].update(evaluation_backend="torch_modular_nas", device=str(device),
                                  dtype="torch.float32", evaluation_mode="sequential_architectures")
    return result


def evaluate_trained_architecture(architecture, saved_result, seed, *, compute=None):
    """Inference on saved tensors only; a new seed changes the evaluation inputs."""
    import torch
    from .devices import resolve_device, synchronize
    settings = _compute_settings(compute); device = resolve_device(settings)
    model = build_torch_model(architecture, 0, device)
    model.load_state_dict({key: torch.tensor(value, dtype=torch.float32, device=device)
                           for key, value in saved_result["metrics"]["trained_state"].items()})
    model.eval()
    inputs = np.random.default_rng(seed+2000).uniform(-1, 1, (128, 2)).astype("float32")
    desired = ((inputs[:, 0] >= 0) != (inputs[:, 1] >= 0)).astype("float32")[:, None]
    with torch.no_grad():
        output = model(torch.from_numpy(inputs).to(device)); labels = torch.from_numpy(desired).to(device)
        loss = float(torch.nn.functional.binary_cross_entropy_with_logits(output, labels))
        accuracy = float(((output >= 0) == labels.bool()).float().mean())
    result = copy.deepcopy(saved_result)
    result.pop("measurement_kind", None)
    result["fitness"] = -loss
    result["objectives"][0] = -loss
    result["metrics"].update(validation_loss=loss, validation_accuracy=accuracy)
    if settings["backend"] == "torch":
        result["metrics"].update(evaluation_backend="torch_modular_nas", device=str(device),
                                  dtype="torch.float32", evaluation_mode="sequential_architectures")
    synchronize(device)
    return result


class ModularNASEngine:
    def __init__(self, spec):
        self.spec = copy.deepcopy(spec); self.method = "modular_nas"
        self.compute = _compute_settings(spec.get("compute"))
        self.seed = int(spec.get("seed", 0)); self.rng = np.random.default_rng(self.seed)
        self.parameters = dict(spec.get("parameters", {})); self.learning = dict(spec.get("learning", {}))
        self.size = int(spec.get("population_size", 6)); self.limit = int(spec.get("generations", 3))
        if self.size < 2 or self.limit < 1:
            raise ValueError("population_size>=2 and generations>=1 are required")
        self.population = [self._new_architecture() for _ in range(self.size)]
        self.parents = [[] for _ in self.population]
        self.generation = 0; self.done = False; self.best = None; self.best_result = None
        self.best_fitness = -float("inf"); self.history = []

    def _new_architecture(self):
        depth = int(self.rng.integers(1, 3))
        return {"widths": [int(self.rng.choice([2, 4, 8])) for _ in range(depth)],
                "activations": [str(self.rng.choice(["tanh", "relu"])) for _ in range(depth)]}

    def _mutate(self, architecture):
        child = copy.deepcopy(architecture); operation = str(self.rng.choice(["width", "activation", "add", "remove"]))
        position = int(self.rng.integers(len(child["widths"])))
        if operation == "add" and len(child["widths"]) < 3:
            child["widths"].insert(position, int(self.rng.choice([2, 4, 8])))
            child["activations"].insert(position, str(self.rng.choice(["tanh", "relu"])))
        elif operation == "remove" and len(child["widths"]) > 1:
            child["widths"].pop(position); child["activations"].pop(position)
        elif operation == "activation":
            child["activations"][position] = "relu" if child["activations"][position] == "tanh" else "tanh"
        else:
            child["widths"][position] = int(self.rng.choice([2, 4, 8]))
        return child

    def _evaluate(self, architecture, seed):
        return train_architecture(architecture, seed, int(self.learning.get("steps", 60)),
                                  float(self.learning.get("learning_rate", .05)),
                                  int(self.learning.get("train_size", 64)),
                                  compute=getattr(self, "compute", None))

    def step(self, ctx):
        if self.done:
            return
        scores, results = [], []
        for index, architecture in enumerate(self.population):
            result = ctx.evaluate({"encoding": "modular_mlp", **architecture},
                lambda a=architecture: self._evaluate(a, self.seed),
                label=f"modular_nas:{self.generation}:{index}")
            score = float(result["fitness"]); scores.append(score); results.append(result)
            if score > self.best_fitness:
                self.best_fitness = score; self.best = copy.deepcopy(architecture); self.best_result = copy.deepcopy(result)
        order = np.argsort(-np.asarray(scores)); elite = self.population[int(order[0])]
        event = {"kind": "nas_generation", "generation": self.generation, "architectures": self.population,
                 "parents": self.parents, "fitness": scores,
                 "training_steps_per_candidate": int(self.learning.get("steps", 60))}
        self.history.append(copy.deepcopy(event)); ctx.record(event)
        eligible = order[:max(2, self.size//2)]
        next_population = [copy.deepcopy(elite)]; parents = [[int(order[0])]]
        for _ in range(1, self.size):
            parent = int(self.rng.choice(eligible))
            next_population.append(self._mutate(self.population[parent])); parents.append([parent])
        self.population = next_population; self.parents = parents
        self.generation += 1; self.done = self.generation >= self.limit

    def summary(self):
        return {"method": self.method, "target": "continuous_xor", "generations": self.generation,
                "best_genome": self.best, "best_result": self.best_result,
                "best_fitness": self.best_fitness if self.best else None, "history": self.history,
                "compute": dict(getattr(self, "compute", {"device": "cpu", "backend": "reference", "batch_size": 32})),
                "evaluation_mode": "sequential_architectures",
                "scope": "evolved modular architectures trained independently on a fixed train/validation split"}

    def replay(self, seed=None):
        if self.best is None:
            raise ValueError("No trained architecture to replay")
        return evaluate_trained_architecture(self.best, self.best_result,
                                             self.seed if seed is None else int(seed), compute=getattr(self, "compute", None))


def render_genome(summary, outpath):
    """Render actual saved genes/decoded tensors, without inventing connectivity."""
    from pathlib import Path
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle

    method = summary["method"]
    figure, axes = plt.subplots(1, 2 if method == "hyperneat" else 1,
                                figsize=(13, 5) if method == "hyperneat" else (8, 5), squeeze=False)

    def draw(ax, positions, edges, title, labels=None):
        labels = labels or {}
        largest = max([abs(w) for _, _, w in edges] + [1.])
        for source, destination, weight in edges:
            if source not in positions or destination not in positions or not weight:
                continue
            x0, y0 = positions[source]; x1, y1 = positions[destination]
            ax.plot([x0, x1], [y0, y1], color="#2066a8" if weight > 0 else "#c14e3b",
                    linewidth=.3 + 2*abs(weight)/largest, alpha=.55, zorder=1)
        for key, (x, y) in positions.items():
            ax.add_patch(Circle((x, y), .075, facecolor="#f6f4ed", edgecolor="#22323b", linewidth=1.2, zorder=2))
            ax.text(x, y, labels.get(key, str(key)), fontsize=7, ha="center", va="center", zorder=3)
        ax.set_title(title, fontsize=12, loc="left", pad=18)
        ax.autoscale_view(); ax.margins(.16); ax.axis("off")

    def draw_mlp(ax, matrices, title):
        positions, edges, labels = {}, [], {}
        widths = [matrices[0].shape[0]-1] + [matrix.shape[1] for matrix in matrices]
        for layer, width in enumerate(widths):
            for node in range(width):
                key = (layer, node); positions[key] = (float(layer), float(node-(width-1)/2)*.25)
                labels[key] = str(node)
            if layer < len(matrices):
                key = (layer, "bias"); positions[key] = (float(layer), -(width+1)/2*.25); labels[key] = "b"
        for layer, matrix in enumerate(matrices):
            for source in range(matrix.shape[0]):
                source_key = (layer, source) if source < matrix.shape[0]-1 else (layer, "bias")
                for destination in range(matrix.shape[1]):
                    edges.append((source_key, (layer+1, destination), float(matrix[source, destination])))
        draw(ax, positions, edges, title, labels)

    if (summary.get("best_genome") or {}).get("encoding") == "direct_mlp":
        genome = summary["best_genome"]
        n_inputs, n_outputs = TARGETS[target_name(genome["target"])]
        hidden = int(genome["hidden"]); weights = np.asarray(genome["weights"])
        cut = (n_inputs+1)*hidden
        draw_mlp(axes[0, 0], [weights[:cut].reshape(n_inputs+1, hidden), weights[cut:].reshape(hidden+1, n_outputs)],
                 "Saved direct neural controller")
    elif method == "modular_nas":
        state = summary["best_result"]["metrics"]["trained_state"]
        matrices = []
        for key in sorted((key for key in state if key.endswith(".weight")), key=lambda key: int(key.split(".")[0])):
            prefix = key.split(".")[0]
            matrices.append(np.vstack([np.asarray(state[key]).T, np.asarray(state[prefix+".bias"])]))
        draw_mlp(axes[0, 0], matrices, "Saved trained modular MLP")
    else:
        genome = summary["best_genome"]
        if genome is None:
            plt.close(figure); raise ValueError("No evaluated structural genome to render")
        connections = [gene for gene in genome["connections"] if gene["enabled"]]
        ids = {node["id"] for node in genome["nodes"]} | {gene["source"] for gene in connections}
        layers = {key: 0 for key in ids if key < 0}
        for _ in range(len(ids)+1):
            for key in sorted(ids):
                parents = [gene["source"] for gene in connections if gene["target"] == key]
                if key >= 0 and all(parent in layers for parent in parents):
                    layers[key] = max([layers[parent]+1 for parent in parents] + [1])
        for key in ids:
            layers.setdefault(key, 1)
        positions = {}
        for layer in sorted(set(layers.values())):
            members = sorted(key for key, value in layers.items() if value == layer)
            for index, key in enumerate(members):
                positions[key] = (float(layer), float(index-(len(members)-1)/2)*.35)
        labels = {node["id"]: f"{node['id']}\n{node['activation']}" for node in genome["nodes"]}
        edges = [(gene["source"], gene["target"], gene["weight"]) for gene in connections]
        draw(axes[0, 0], positions, edges, "Evolved CPPN" if method in {"cppn", "hyperneat"} else "Evolved NEAT controller", labels)
        if method == "hyperneat":
            weights = np.asarray(summary["best_result"]["metrics"]["decoded_weights"])
            n_inputs, n_outputs = TARGETS[target_name(summary["target"])]
            hidden = (len(weights)-n_outputs)//(n_inputs+1+n_outputs)
            cut = (n_inputs+1)*hidden
            matrices = [weights[:cut].reshape(n_inputs+1, hidden), weights[cut:].reshape(hidden+1, n_outputs)]
            draw_mlp(axes[0, 1], matrices, "Actual expressed substrate weights")
    figure.text(.02, .015, "Blue: positive weight   Red: negative weight   Width: magnitude   b: bias", fontsize=9)
    figure.tight_layout(rect=(0, .04, 1, 1))
    path = Path(outpath); path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=160, bbox_inches="tight"); plt.close(figure)
    return str(path)


METHODS = {"neat": StructuralEngine, "cppn": StructuralEngine, "hyperneat": StructuralEngine,
           "modular_nas": ModularNASEngine}
