"""Torch phenotype evaluation for the existing canonical NEAT evolution backend.

Only evaluation is accelerated. Genomes, historical markings, crossover,
speciation and reproduction remain NEAT-Python's canonical adapter. Expressed
feed-forward networks are compiled into groups sharing depth and node functions;
each group executes across candidates and observations with padded tensor links.
This is an eager evaluator, not TensorNEAT or a replacement evolutionary method.
CPU defaults to float64; CUDA/MPS default to float32, so trajectories near action
or collision boundaries can differ from the scalar float64 reference.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import neat
import neat.activations as neat_activations
import neat.aggregations as neat_aggregations
import torch


ACTIVATIONS = {name.removesuffix("_activation"): function
               for name, function in vars(neat_activations).items()
               if name.endswith("_activation") and callable(function) and name != "validate_activation"}
AGGREGATIONS = {name.removesuffix("_aggregation"): function
                for name, function in vars(neat_aggregations).items()
                if name.endswith("_aggregation") and callable(function) and name != "validate_aggregation"}
# Explicit support contracts: newly introduced upstream functions must be audited.
SUPPORTED_ACTIVATIONS = frozenset({"sigmoid", "tanh", "sin", "gauss", "relu", "elu", "lelu", "selu",
                                   "softplus", "identity", "clamped", "inv", "log", "exp", "abs", "hat",
                                   "square", "cube"})
SUPPORTED_AGGREGATIONS = frozenset({"sum", "product", "max", "min", "maxabs", "median", "mean"})


def evaluation_dtype(device, dtype=None):
    device = torch.device(device)
    dtype = dtype or (torch.float64 if device.type == "cpu" else torch.float32)
    if dtype not in (torch.float32, torch.float64):
        raise ValueError("Torch NEAT evaluation supports float32 or float64 only")
    if device.type == "mps" and dtype == torch.float64:
        raise ValueError("MPS does not support float64; request float32 explicitly or use CPU")
    return dtype


def activate(name, values):
    """Match NEAT-Python's built-in scales/clamps, not torch default activations."""
    if name == "sigmoid": return torch.sigmoid((5*values).clamp(-60, 60))
    if name == "tanh": return torch.tanh((2.5*values).clamp(-60, 60))
    if name == "sin": return torch.sin((5*values).clamp(-60, 60))
    if name == "gauss": return torch.exp(-5*values.clamp(-3.4, 3.4).square())
    if name == "relu": return values.clamp_min(0)
    if name == "elu": return torch.where(values > 0, values, torch.exp(values.clamp_max(0))-1)
    if name == "lelu": return torch.where(values > 0, values, .005*values)
    if name == "selu":
        return 1.0507009873554804934193349852946 * torch.where(
            values > 0, values, 1.6732632423543772848170429916717*(torch.exp(values.clamp_max(0))-1))
    if name == "softplus": return .2*torch.log(1+torch.exp((5*values).clamp(-60, 60)))
    if name == "identity": return values
    if name == "clamped": return values.clamp(-1, 1)
    if name == "inv": return torch.where(values == 0, torch.zeros_like(values), values.reciprocal())
    if name == "log": return torch.log(values.clamp_min(1e-7))
    if name == "exp": return torch.exp(values.clamp(-60, 60))
    if name == "abs": return values.abs()
    if name == "hat": return (1-values.abs()).clamp_min(0)
    if name == "square": return values.square()
    if name == "cube": return values.pow(3)
    raise ValueError(f"Unsupported torch NEAT activation: {name!r}")


def aggregate(name, values, mask):
    """Reduce ordered incoming weighted links, preserving empty-node semantics."""
    # values [node, case, incoming]; mask [node, incoming]. Padding is not an edge.
    valid = mask[:, None, :]
    count = mask.sum(-1)[:, None]
    if name == "sum": return torch.where(valid, values, 0.).sum(-1)
    if name == "product": return torch.where(valid, values, 1.).prod(-1)
    if name == "mean": return torch.where(valid, values, 0.).sum(-1)/count.clamp_min(1)
    if name == "max": result = values.masked_fill(~valid, -float("inf")).amax(-1)
    elif name == "min": result = values.masked_fill(~valid, float("inf")).amin(-1)
    elif name == "maxabs":
        index = values.abs().masked_fill(~valid, -float("inf")).argmax(-1, keepdim=True)
        result = values.gather(-1, index).squeeze(-1)
    elif name == "median":
        ordered = values.masked_fill(~valid, float("inf")).sort(-1).values
        lower = ((count-1).clamp_min(0)//2).expand(-1, values.shape[1]).unsqueeze(-1)
        upper = (count//2).expand(-1, values.shape[1]).unsqueeze(-1)
        result = .5*(ordered.gather(-1, lower).squeeze(-1)+ordered.gather(-1, upper).squeeze(-1))
    else:
        raise ValueError(f"Unsupported torch NEAT aggregation: {name!r}")
    return torch.where(count > 0, result, torch.zeros_like(result))


@dataclass
class _NodeGroup:
    activation: str
    aggregation: str
    candidates: torch.Tensor
    destinations: torch.Tensor
    sources: torch.Tensor
    weights: torch.Tensor
    mask: torch.Tensor
    bias: torch.Tensor
    response: torch.Tensor


class TorchFeedForwardBatch:
    """Heterogeneous NEAT phenotypes; input/output contract is [candidate,case,unit]."""
    def __init__(self, genomes, config, *, device="cpu", dtype=None):
        if not config.genome_config.feed_forward:
            raise ValueError("Torch structural backend supports feed-forward NEAT phenotypes only")
        if not genomes:
            raise ValueError("At least one genome is required")
        self.device = torch.device(device); self.dtype = evaluation_dtype(self.device, dtype)
        self.count = len(genomes)
        self.input_keys = list(config.genome_config.input_keys)
        self.output_keys = list(config.genome_config.output_keys)
        self.n_inputs = len(self.input_keys); self.n_outputs = len(self.output_keys)
        activation_names = {function: name for name, function in ACTIVATIONS.items() if name in SUPPORTED_ACTIVATIONS}
        aggregation_names = {function: name for name, function in AGGREGATIONS.items() if name in SUPPORTED_AGGREGATIONS}
        grouped = defaultdict(list); slot_counts = []
        for candidate, genome in enumerate(genomes):
            network = neat.nn.FeedForwardNetwork.create(genome, config)
            keys = self.input_keys + self.output_keys + [node for node, *_ in network.node_evals if node not in self.output_keys]
            slots = {key: index for index, key in enumerate(keys)}
            slot_counts.append(len(slots))
            depth = {key: 0 for key in self.input_keys + self.output_keys}
            for node, activation, aggregation, bias, response, links in network.node_evals:
                if activation not in activation_names:
                    raise ValueError(f"Unsupported torch NEAT activation for node {node}; custom functions cannot be substituted")
                if aggregation not in aggregation_names:
                    raise ValueError(f"Unsupported torch NEAT aggregation for node {node}; custom functions cannot be substituted")
                if any(source not in depth for source, _ in links):
                    raise ValueError("NEAT phenotype contains an unresolved feed-forward dependency")
                layer = 1+max([depth[source] for source, _ in links] or [0]); depth[node] = layer
                group_key = (layer, activation_names[activation], aggregation_names[aggregation])
                grouped[group_key].append((candidate, slots[node], bias, response,
                                           [(slots[source], weight) for source, weight in links]))
        self.slots = max(slot_counts); self.groups = []
        for (_, activation_name, aggregation_name), nodes in sorted(grouped.items()):
            width = max(1, max(len(node[4]) for node in nodes))
            sources, weights, masks = [], [], []
            for _, _, _, _, links in nodes:
                padding = width-len(links)
                sources.append([source for source, _ in links] + [0]*padding)
                weights.append([weight for _, weight in links] + [0.]*padding)
                masks.append([True]*len(links) + [False]*padding)
            self.groups.append(_NodeGroup(
                activation_name, aggregation_name,
                torch.tensor([node[0] for node in nodes], dtype=torch.long, device=self.device),
                torch.tensor([node[1] for node in nodes], dtype=torch.long, device=self.device),
                torch.tensor(sources, dtype=torch.long, device=self.device),
                torch.tensor(weights, dtype=self.dtype, device=self.device),
                torch.tensor(masks, dtype=torch.bool, device=self.device),
                torch.tensor([node[2] for node in nodes], dtype=self.dtype, device=self.device),
                torch.tensor([node[3] for node in nodes], dtype=self.dtype, device=self.device)))

    @torch.no_grad()
    def __call__(self, observations):
        observations = torch.as_tensor(observations, dtype=self.dtype, device=self.device)
        if observations.ndim != 3 or observations.shape[0] != self.count or observations.shape[2] != self.n_inputs:
            raise ValueError(f"Expected observations [{self.count}, cases, {self.n_inputs}]")
        cases = observations.shape[1]
        values = torch.zeros((self.count, cases, self.slots), dtype=self.dtype, device=self.device)
        values[:, :, :self.n_inputs] = observations
        for group in self.groups:
            sources = values[group.candidates].gather(2, group.sources[:, None, :].expand(-1, cases, -1))
            weighted = sources*group.weights[:, None, :]
            reduced = aggregate(group.aggregation, weighted, group.mask)
            outputs = activate(group.activation, group.bias[:, None]+group.response[:, None]*reduced)
            values[group.candidates, :, group.destinations] = outputs
        return values[:, :, self.n_inputs:self.n_inputs+self.n_outputs]


def decode_cppn_batch(cppns: TorchFeedForwardBatch, n_inputs, hidden, n_outputs, threshold=.2, weight_scale=3.):
    """Batched fixed-substrate decoding using precisely the scalar decoder's queries."""
    if not 0 <= threshold < 1:
        raise ValueError("CPPN expression threshold must be in [0,1)")
    if min(n_inputs, hidden, n_outputs) < 1:
        raise ValueError("Substrate layer widths must be positive")
    if cppns.n_inputs != 5:
        raise ValueError("HyperNEAT CPPNs require five coordinate-query inputs")
    from .structural import substrate_coordinates
    # Geometric construction is metadata, not a scalar fallback for CPPN inference.
    layers = [substrate_coordinates(n_inputs, -1.), substrate_coordinates(hidden, 0.),
              substrate_coordinates(n_outputs, 1.)]
    queries = []
    for sources, destinations in zip(layers[:-1], layers[1:]):
        import numpy as np
        sources = np.vstack([sources, [0., sources[0, 1]-.25]])
        for source in sources:
            for destination in destinations:
                queries.append([*source, *destination, float(np.linalg.norm(source-destination))])
    query = torch.tensor(queries, dtype=cppns.dtype, device=cppns.device)
    expression = torch.tanh(cppns(query[None].expand(cppns.count, -1, -1))[:, :, 0])
    return expression.sign()*(expression.abs()-threshold).clamp_min(0)/(1-threshold)*weight_scale


class _SubstratePolicy:
    def __init__(self, weights, n_inputs, hidden, n_outputs, target):
        cut = (n_inputs+1)*hidden
        self.first = weights[:, :cut].reshape(-1, n_inputs+1, hidden)
        self.second = weights[:, cut:].reshape(-1, hidden+1, n_outputs)
        self.target = target

    def __call__(self, observations):
        inputs = torch.cat([observations, torch.ones_like(observations[:, :, :1])], -1)
        hidden = torch.tanh(torch.bmm(inputs, self.first))
        hidden = torch.cat([hidden, torch.ones_like(hidden[:, :, :1])], -1)
        output = torch.bmm(hidden, self.second)
        return torch.sigmoid(output.clamp(-60, 60)) if self.target == "xor" else torch.tanh(output)


@torch.no_grad()
def evaluate_structural_batch(genomes, config, method, target, seed, parameters=None, compute=None):
    """Execute only the supplied uncached candidates; call inside ctx.evaluate_batch."""
    from .devices import resolve_device, synchronize
    from .accelerator_search import evaluate_policies_batch
    from .search import TARGETS
    parameters = parameters or {}; compute = compute or {"device": "cpu", "backend": "torch"}
    device = resolve_device(compute); dtype = evaluation_dtype(device)
    networks = TorchFeedForwardBatch(genomes, config, device=device, dtype=dtype)
    if method == "cppn":
        resolution = int(parameters.get("resolution", 9))
        if resolution < 1: raise ValueError("Pattern resolution must be positive")
        axis = torch.linspace(-1, 1, resolution, dtype=dtype, device=device)
        y, x = torch.meshgrid(axis, axis, indexing="ij"); radius = torch.sqrt(x.square()+y.square())
        queries = torch.stack([x, y, radius, torch.ones_like(x)], -1).reshape(-1, 4)
        pixels = .5+.5*torch.tanh(networks(queries[None].expand(len(genomes), -1, -1))[:, :, 0])
        desired = .5+.5*torch.cos(2*torch.pi*radius.flatten())
        errors = (pixels-desired).square().mean(-1)
        descriptors = torch.stack([pixels.mean(-1), pixels.std(-1, correction=0)], -1)
        synchronize(device)
        image_data = pixels.reshape(-1, resolution, resolution).cpu().tolist()
        results = [{"fitness": 1-float(error), "descriptor": descriptor, "constraints": True,
                    "metrics": {"mse": float(error), "resolution": resolution, "pixels": image}}
                   for error, descriptor, image in zip(errors.cpu().tolist(), descriptors.cpu().tolist(), image_data)]
    elif method == "hyperneat":
        n_inputs, n_outputs = TARGETS[target]; hidden = int(parameters.get("hidden", 4))
        weights = decode_cppn_batch(networks, n_inputs, hidden, n_outputs,
                                    float(parameters.get("expression_threshold", .2)),
                                    float(parameters.get("weight_scale", 3.)))
        policy = _SubstratePolicy(weights, n_inputs, hidden, n_outputs, target)
        results = evaluate_policies_batch(policy, target, [seed]*len(genomes), parameters, device=device, dtype=dtype)
        energy = weights.square().mean(-1).cpu().tolist()
        expressed = (weights != 0).sum(-1).cpu().tolist(); decoded = weights.cpu().tolist()
        for result, magnitude, count, genes in zip(results, energy, expressed, decoded):
            result["objectives"] = [float(result["fitness"]), -magnitude]
            result["metrics"].update(weight_mean_square=magnitude, substrate_parameters=len(genes),
                                      expressed_connections=count, decoded_weights=genes)
    elif method == "neat":
        results = evaluate_policies_batch(networks, target, [seed]*len(genomes), parameters, device=device, dtype=dtype)
    else:
        raise ValueError(f"Unsupported structural evaluation method: {method!r}")
    synchronize(device)
    for result in results:
        result["metrics"].update(evaluation_backend="torch_neat_phenotype", device=str(device),
                                  dtype=str(dtype))
    return results
