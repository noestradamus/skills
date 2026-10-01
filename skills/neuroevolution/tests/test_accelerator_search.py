"""Independent scalar comparisons and dispatch contracts for tensor batches."""
import pickle

import numpy as np
import pytest
import torch

from neuroevolution_lab.accelerator_search import evaluate_controllers_batch, evaluate_policies_batch
from neuroevolution_lab.search import METHODS, SearchEngine, evaluate_controller, evaluate_policy, parameter_count


DEVICES = [
    "cpu",
    pytest.param("mps", marks=pytest.mark.skipif(not torch.backends.mps.is_available(), reason="MPS unavailable")),
    pytest.param("cuda", marks=pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA unavailable")),
]


def assert_result_close(actual, expected, tolerance=1e-11):
    assert actual.keys() == expected.keys()
    for key in actual:
        if isinstance(actual[key], dict):
            assert_result_close(actual[key], expected[key], tolerance)
        elif isinstance(actual[key], bool):
            assert actual[key] is expected[key]
        else:
            np.testing.assert_allclose(actual[key], expected[key], atol=tolerance, rtol=tolerance)


@pytest.mark.parametrize("device", DEVICES)
@pytest.mark.parametrize("target", ["xor", "cartpole", "navigation"])
def test_population_and_environments_match_independent_scalar_reference(device, target):
    params = {"hidden": 5, "episodes": 4, "horizon": 90}
    weights = np.random.default_rng(202).normal(size=(7, parameter_count(target, 5)))
    seeds = [2, 40, 9, 101, 73, 38, 900]
    batch = evaluate_controllers_batch(weights, target, seeds, params, device=device)
    tolerance = 1e-11 if device == "cpu" else 5e-5
    for index, result in enumerate(batch):
        scalar = evaluate_controller(weights[index], target, seeds[index], params)
        assert_result_close(result, scalar, tolerance)


@pytest.mark.parametrize("device", DEVICES)
def test_batched_navigation_masks_finished_candidates_and_preserves_wall_collision(device):
    seen_shapes = []

    def policy(observations):
        seen_shapes.append(tuple(observations.shape))
        x, y = observations[1, :, 0], observations[1, :, 1]
        detour_x = torch.where(x < .52, torch.where(y < .85, 0., 1.), torch.where(x < .88, 1., 0.))
        detour_y = torch.where(x < .52, torch.where(y < .85, 1., 0.), torch.where(y > .52, -1., 0.))
        result = torch.zeros((*observations.shape[:2], 2), device=observations.device, dtype=observations.dtype)
        result[0, :, 0] = 1.
        result[1] = torch.stack((detour_x, detour_y), dim=-1)
        return result

    def scalar_detour(x):
        if x[0] < .52:
            return [0, 1] if x[1] < .85 else [1, 0]
        return [1 if x[0] < .88 else 0, -1 if x[1] > .52 else 0]

    actual = evaluate_policies_batch(policy, "navigation", [2, 9, 15], device=device)
    references = [evaluate_policy(fn, "navigation", seed) for fn, seed in
                  zip([lambda x: [1., 0.], scalar_detour, lambda x: [0., 0.]], [2, 9, 15])]
    for result, expected in zip(actual, references):
        assert_result_close(result, expected, 1e-11 if device == "cpu" else 5e-5)
    assert actual[0]["metrics"]["collisions"] > 0
    assert actual[1]["metrics"]["success"]
    assert len(actual[1]["metrics"]["trajectory"]) < len(actual[2]["metrics"]["trajectory"])
    assert set(seen_shapes) == {(3, 1, 4)}


def test_cartpole_policy_observes_population_times_episode_batch():
    seen_shapes = []

    def policy(observations):
        seen_shapes.append(tuple(observations.shape))
        return torch.zeros((*observations.shape[:2], 1), device=observations.device, dtype=observations.dtype)

    actual = evaluate_policies_batch(policy, "cartpole", [3, 14, 92], {"episodes": 5, "horizon": 70})
    for result, seed in zip(actual, [3, 14, 92]):
        expected = evaluate_policy(lambda x: [0.], "cartpole", seed, {"episodes": 5, "horizon": 70})
        assert_result_close(result, expected)
    assert set(seen_shapes) == {(3, 5, 4)}


class DispatchContext:
    """A dispatch fixture verifies batching; production budget tests own budgets."""
    def __init__(self):
        self.events = []
        self.batch_sizes = []
        self.evaluations = []
        self.dispatched = False

    def evaluate(self, genome, fn, label=""):
        self.dispatched = True
        result = fn()
        self.evaluations.append((genome, result, label))
        return result

    def evaluate_batch(self, genomes, fn, labels=None, kind="observed"):
        self.dispatched = True
        self.batch_sizes.append(len(genomes))
        results = fn(list(range(len(genomes))))
        self.evaluations.extend(zip(genomes, results, labels))
        return results

    def record(self, event):
        self.events.append(event)


@pytest.mark.parametrize("method", list(METHODS))
def test_all_search_methods_use_chunked_population_execution_and_resume(method):
    spec = {"method": method, "seed": 7, "population_size": 6, "generations": 2,
            "compute": {"backend": "torch", "device": "cpu", "batch_size": 4}}
    reference = SearchEngine({key: value for key, value in spec.items() if key != "compute"})
    engine = SearchEngine(spec)
    context, scalar_context = DispatchContext(), DispatchContext()
    engine.step(context)
    reference.step(scalar_context)
    assert context.batch_sizes == ([1] if method == "fixed_controller" else [4, 2])
    for (_, actual, _), (_, expected, _) in zip(context.evaluations, scalar_context.evaluations):
        assert_result_close(actual, expected)
    resumed = pickle.loads(pickle.dumps(engine))
    engine.step(context)
    resumed_context = DispatchContext()
    resumed.step(resumed_context)
    assert engine.summary() == resumed.summary()
    assert_result_close(engine.replay(), engine.best_result)


def test_search_evaluates_only_uncached_dispatched_indices(monkeypatch):
    import neuroevolution_lab.accelerator_search as accelerator
    engine = SearchEngine({"method": "ga", "target": "xor", "seed": 5,
                           "population_size": 6, "generations": 1,
                           "compute": {"backend": "torch", "device": "cpu", "batch_size": 6}})
    original = engine.population.copy()
    expected = [evaluate_controller(weights, "xor", 5) for weights in original]
    calls = []
    actual_function = accelerator.evaluate_controllers_batch

    class PartialCacheContext(DispatchContext):
        def evaluate_batch(self, genomes, fn, labels=None, kind="observed"):
            self.dispatched = True
            uncached = [1, 4]
            new = fn(uncached)
            results = list(expected)
            for index, value in zip(uncached, new):
                results[index] = value
            return results

    context = PartialCacheContext()

    def check_dispatch(weights, *args, **kwargs):
        assert context.dispatched
        calls.append(np.array(weights))
        return actual_function(weights, *args, **kwargs)

    monkeypatch.setattr(accelerator, "evaluate_controllers_batch", check_dispatch)
    engine.step(context)
    assert len(calls) == 1
    np.testing.assert_array_equal(calls[0], original[[1, 4]])


def test_batch_validation_and_empty_population():
    assert evaluate_controllers_batch([], "xor", [], device="cpu") == []
    with pytest.raises(ValueError, match="shape"):
        evaluate_controllers_batch(np.zeros((2, 3)), "xor", [0, 1], device="cpu")
    with pytest.raises(ValueError, match="horizon"):
        evaluate_policies_batch(lambda x: x, "cartpole", [0], {"horizon": 0})
