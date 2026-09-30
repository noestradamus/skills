"""Tensor-batched controller evaluation with the scalar environments as reference.

The policy contract is [candidate, environment/case, input] ->
[candidate, environment/case, output]. Candidate and environment axes stay on the
selected device throughout rollout. NumPy only produces the same seeded initial
conditions as the reference; JSON conversion occurs after the batched rollout.
"""
from __future__ import annotations

import math
from collections.abc import Callable, Sequence

import numpy as np
import torch

from .search import TARGETS, parameter_count, target_name


def evaluation_dtype(device: torch.device | str) -> torch.dtype:
    """Reference precision on CPU; accelerator-friendly precision elsewhere."""
    return torch.float64 if torch.device(device).type == "cpu" else torch.float32


@torch.no_grad()
def evaluate_policies_batch(
    policy: Callable[[torch.Tensor], torch.Tensor],
    target: str,
    seeds: Sequence[int],
    parameters: dict | None = None,
    *,
    device: torch.device | str = "cpu",
    dtype: torch.dtype | None = None,
) -> list[dict]:
    """Execute independent policies and seeded environments in one tensor batch.

    ``policy`` must preserve candidate ordering and support an arbitrary second
    axis. It receives four XOR cases, ``episodes`` CartPole environments, or one
    navigation environment per candidate. It must already reside on ``device``.
    This function does no journal/budget dispatch: callers must dispatch first.
    """
    target = target_name(target)
    parameters = parameters or {}
    device = torch.device(device)
    dtype = dtype or evaluation_dtype(device)
    seeds = [int(seed) for seed in seeds]
    count = len(seeds)
    if count == 0:
        return []

    if target == "xor":
        inputs = torch.tensor([[0., 0.], [0., 1.], [1., 0.], [1., 1.]],
                              device=device, dtype=dtype).expand(count, -1, -1)
        outputs = policy(inputs)[..., 0]
        desired = torch.tensor([0., 1., 1., 0.], device=device, dtype=dtype)
        losses = (outputs - desired).square().mean(dim=1)
        accuracies = ((outputs >= .5) == desired.bool()).to(dtype).mean(dim=1)
        finite = torch.isfinite(outputs).all(dim=1)
        predictions = outputs.cpu().tolist()
        return [{"fitness": 1. - loss, "descriptor": [row[1], row[2]],
                 "constraints": valid,
                 "metrics": {"mse": loss, "accuracy": accuracy,
                             "predictions": row, "episodes": 1}}
                for row, loss, accuracy, valid in
                zip(predictions, losses.cpu().tolist(), accuracies.cpu().tolist(), finite.cpu().tolist())]

    horizon = int(parameters.get("horizon", 200 if target == "cartpole" else 80))
    if horizon < 1:
        raise ValueError("Controller horizon must be positive")
    if target == "cartpole":
        episodes = int(parameters.get("episodes", 3))
        if episodes < 1:
            raise ValueError("CartPole episodes must be positive")
        initial = np.array([[np.random.default_rng(seed + episode).uniform(-.05, .05, 4)
                             for episode in range(episodes)] for seed in seeds])
        state = torch.as_tensor(initial, device=device, dtype=dtype)
        alive = torch.ones((count, episodes), device=device, dtype=torch.bool)
        returns = torch.zeros((count, episodes), device=device, dtype=torch.int64)
        position_sum = torch.zeros((count, episodes), device=device, dtype=dtype)
        angle_sum = torch.zeros_like(position_sum)
        for _ in range(horizon):
            x, x_dot, theta, theta_dot = state.unbind(dim=-1)
            action = policy(state)[..., 0]
            force = torch.where(action >= 0, 10., -10.)
            cosine, sine = theta.cos(), theta.sin()
            temp = (force + .05 * theta_dot.square() * sine) / 1.1
            theta_acc = (9.8 * sine - cosine * temp) / (.5 * (4 / 3 - .1 * cosine.square() / 1.1))
            x_acc = temp - .05 * theta_acc * cosine / 1.1
            following = torch.stack((x + .02*x_dot, x_dot + .02*x_acc,
                                     theta + .02*theta_dot, theta_dot + .02*theta_acc), dim=-1)
            state = torch.where(alive[..., None], following, state)
            returns += alive.to(torch.int64)
            position_sum += torch.where(alive, state[..., 0], 0.)
            angle_sum += torch.where(alive, state[..., 2], 0.)
            alive = alive & (state[..., 0].abs() <= 2.4) & (state[..., 2].abs() <= 12 * math.pi / 180)
        descriptors = torch.stack(((position_sum / returns).mean(dim=1),
                                   (angle_sum / returns).mean(dim=1)), dim=-1)
        rewards = returns.to(dtype).mean(dim=1)
        return [{"fitness": fitness, "descriptor": descriptor, "constraints": True,
                 "metrics": {"returns": episode_returns, "episodes": episodes, "horizon": horizon}}
                for fitness, descriptor, episode_returns in
                zip(rewards.cpu().tolist(), descriptors.cpu().tolist(), returns.cpu().tolist())]

    initial = np.array([np.array([.1, .5]) + np.random.default_rng(seed).uniform(-.01, .01, 2)
                        for seed in seeds])
    position = torch.as_tensor(initial, device=device, dtype=dtype)
    goal = torch.tensor([.9, .5], device=device, dtype=dtype)
    alive = torch.ones(count, device=device, dtype=torch.bool)
    steps = torch.zeros(count, device=device, dtype=torch.int64)
    collisions = torch.zeros_like(steps)
    paths = torch.empty((count, horizon + 1, 2), device=device, dtype=dtype)
    paths[:, 0] = position
    for step in range(horizon):
        observation = torch.cat((position, goal - position), dim=-1)[:, None, :]
        velocity = policy(observation)[:, 0].clamp(-1, 1)
        proposal = (position + .04 * velocity).clamp(0, 1)
        crossing = ((position[:, 0] < .5) & (proposal[:, 0] >= .5)) | (
                    (proposal[:, 0] < .5) & (position[:, 0] >= .5))
        delta_x = proposal[:, 0] - position[:, 0]
        denominator = torch.where(crossing, delta_x, torch.ones_like(delta_x))
        crossing_y = position[:, 1] + (.5-position[:, 0]) * (proposal[:, 1]-position[:, 1]) / denominator
        blocked = crossing & (crossing_y < .8)
        proposal[:, 0] = torch.where(blocked, position[:, 0], proposal[:, 0])
        collisions += (alive & blocked).to(torch.int64)
        position = torch.where(alive[:, None], proposal, position)
        paths[:, step + 1] = position
        steps += alive.to(torch.int64)
        alive = alive & (torch.linalg.vector_norm(position - goal, dim=-1) >= .06)
    distances = torch.linalg.vector_norm(position - goal, dim=-1).cpu().tolist()
    descriptors, all_paths = position.cpu().tolist(), paths.cpu().tolist()
    return [{"fitness": -distance, "descriptor": descriptor, "constraints": True,
             "metrics": {"distance": distance, "success": distance < .06,
                         "collisions": collision_count, "trajectory": path[:length + 1], "episodes": 1}}
            for distance, descriptor, collision_count, path, length in
            zip(distances, descriptors, collisions.cpu().tolist(), all_paths, steps.cpu().tolist())]


@torch.no_grad()
def evaluate_controllers_batch(
    weights, target: str, seeds: Sequence[int], parameters: dict | None = None,
    *, compute: dict | None = None, device: torch.device | str | None = None,
    dtype: torch.dtype | None = None,
) -> list[dict]:
    """Evaluate a population of flat MLPs without a Python candidate loop."""
    parameters = parameters or {}
    target = target_name(target)
    seeds = list(seeds)
    if not seeds:
        return []
    if device is None:
        from .devices import resolve_device
        device = resolve_device(compute or {"device": "cpu"})
    device = torch.device(device)
    dtype = dtype or evaluation_dtype(device)
    hidden = int(parameters.get("hidden", 4))
    population = torch.as_tensor(np.asarray(weights), device=device, dtype=dtype)
    if population.shape != (len(seeds), parameter_count(target, hidden)):
        raise ValueError("Controller batch shape does not match its seeds and topology")
    n_in, n_out = TARGETS[target]
    cut = (n_in + 1) * hidden
    first = population[:, :cut].reshape(-1, n_in + 1, hidden)
    second = population[:, cut:].reshape(-1, hidden + 1, n_out)

    def policy(observations):
        hidden_state = torch.tanh(torch.bmm(observations, first[:, :n_in]) + first[:, n_in, None, :])
        output = torch.bmm(hidden_state, second[:, :hidden]) + second[:, hidden, None, :]
        return torch.sigmoid(output.clamp(-60, 60)) if target == "xor" else output.tanh()

    results = evaluate_policies_batch(policy, target, seeds, parameters, device=device, dtype=dtype)
    complexities = population.square().mean(dim=1).cpu().tolist()
    for result, complexity in zip(results, complexities):
        result["objectives"] = [float(result["fitness"]), -complexity]
        result["metrics"]["weight_mean_square"] = complexity
    return results
