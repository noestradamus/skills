"""Population tensor kernels, independent of search and evaluation accounting.

Each row has its own parameters and independent gradient norm. Summing per-row
losses therefore produces the same SGD update as individually trained networks;
averaging across the population would incorrectly shrink their learning rate.
"""
from __future__ import annotations

import numpy as np
import torch


def sine_population_forward(weights: torch.Tensor, inputs: torch.Tensor, hidden: int) -> torch.Tensor:
    """Evaluate P flattened 1-H-1 tanh networks on the same N inputs."""
    if weights.ndim != 2 or weights.shape[1] != 3 * hidden + 1:
        raise ValueError("expected [population, 3 * hidden + 1] dense-network weights")
    w1 = weights[:, :hidden, None]
    b1 = weights[:, hidden:2*hidden]
    w2 = weights[:, 2*hidden:3*hidden, None]
    b2 = weights[:, -1:]
    activations = torch.tanh(torch.matmul(inputs[None], w1.transpose(1, 2)) + b1[:, None])
    return torch.bmm(activations, w2) + b2[:, None]


def refine_sine_population(weights: np.ndarray, hidden: int, task: tuple[float, float],
                           support_seed: int, query_seed: int, steps: int, lr: float,
                           device: str | torch.device = "cpu") -> tuple[np.ndarray, list[dict]]:
    from .learning import sine_task
    if steps < 0 or lr <= 0:
        raise ValueError("nonnegative steps and positive learning rate required")
    live = torch.tensor(weights, dtype=torch.float32, device=device, requires_grad=True)
    original = live.detach().clone()
    x, y = (t.to(device) for t in sine_task(support_seed, task=task))
    qx, qy = (t.to(device) for t in sine_task(query_seed, 48, task))
    with torch.no_grad():
        initial = ((sine_population_forward(live, qx, hidden) - qy[None])**2).mean((1, 2))
    for _ in range(steps):
        losses = ((sine_population_forward(live, x, hidden) - y[None])**2).mean((1, 2))
        gradients, = torch.autograd.grad(losses.sum(), live)
        # Match clip_grad_norm_(all parameters of ONE model, 10).
        scale = torch.clamp(10. / (torch.linalg.vector_norm(gradients, dim=1) + 1e-6), max=1.)
        with torch.no_grad():
            live.add_(gradients * scale[:, None], alpha=-lr)
    with torch.no_grad():
        final = ((sine_population_forward(live, qx, hidden) - qy[None])**2).mean((1, 2))
        delta = torch.linalg.vector_norm(live - original, dim=1)
    metrics = torch.stack([initial, final, delta], dim=1).detach().cpu().numpy()
    return live.detach().cpu().numpy(), [
        {"initial_query_mse": float(row[0]), "query_mse": float(row[1]),
         "parameter_delta_l2": float(row[2]), "gradient_steps": steps}
        for row in metrics]


def batched_lm_logits(states: dict[str, torch.Tensor], tokens: torch.Tensor) -> torch.Tensor:
    """Exact single-layer GRU equations over [P,N,T,H], shared input tokens.

    Uses PyTorch's reset/update/new gate ordering and reset-after hidden bias
    placement. We keep the recurrence over time, while population and sequence
    axes execute together. No approximate model or surrogate is introduced.
    """
    embedded = states["embedding.weight"][:, tokens]
    population, sequences, steps, hidden = embedded.shape
    h = torch.zeros(population, sequences, hidden, device=embedded.device, dtype=embedded.dtype)
    w_ih, w_hh = states["recurrent.weight_ih_l0"], states["recurrent.weight_hh_l0"]
    b_ih, b_hh = states["recurrent.bias_ih_l0"], states["recurrent.bias_hh_l0"]
    inputs = torch.matmul(embedded.reshape(population, sequences*steps, hidden), w_ih.transpose(1, 2))
    inputs = inputs.reshape(population, sequences, steps, 3*hidden) + b_ih[:, None, None]
    outputs = []
    for t in range(steps):
        gates_h = torch.bmm(h, w_hh.transpose(1, 2)) + b_hh[:, None]
        ir, iz, inn = inputs[:, :, t].chunk(3, dim=-1)
        hr, hz, hn = gates_h.chunk(3, dim=-1)
        reset, update = torch.sigmoid(ir+hr), torch.sigmoid(iz+hz)
        new = torch.tanh(inn + reset*hn)
        h = (1.-update)*new + update*h
        outputs.append(torch.bmm(h, states["output.weight"].transpose(1, 2)) + states["output.bias"][:, None])
    return torch.stack(outputs, dim=2)


def lm_population_results(states: dict[str, torch.Tensor], data: torch.Tensor) -> list[dict]:
    from .models import state_digest, VOCABULARY
    with torch.no_grad():
        logits = batched_lm_logits(states, data[:, :-1])
        population, sequences, steps, _ = logits.shape
        targets = data[None, :, 1:].expand(population, -1, -1)
        losses = torch.nn.functional.cross_entropy(logits.reshape(-1, VOCABULARY), targets.reshape(-1),
                                                   reduction="none").reshape(population, sequences, steps)
        loss = losses.mean((1, 2))
        domains = torch.stack([losses[:, data[:, 0] == marker].mean((1, 2)) for marker in (10, 11)], dim=1)
        accuracy = (logits.argmax(-1) == targets).float().mean((1, 2))
    records = torch.cat([loss[:, None], domains, accuracy[:, None]], dim=1).cpu().numpy()
    # One synchronization/transfer per tensor for immutable evidence hashing.
    host_states = {name: value.detach().cpu() for name, value in states.items()}
    return [{"fitness": -float(row[0]), "descriptor": row[1:3].tolist(), "constraints": True,
             "metrics": {"next_token_loss": float(row[0]), "token_accuracy": float(row[3]),
                         "domain_losses": row[1:3].tolist(),
                         "tensor_hash": state_digest({name: value[i] for name, value in host_states.items()}),
                         "sequence_count": len(data), "vocabulary_size": VOCABULARY,
                         "teacher_forced_tokens": len(data)*(data.shape[1]-1)}}
            for i, row in enumerate(records)]
