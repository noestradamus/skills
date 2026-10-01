import pickle

import numpy as np
import pytest

from neuroevolution_lab.search import (
    METHODS, SearchEngine, evaluate_controller, evaluate_policy,
    novelty_and_competition, parameter_count, pareto_order,
)


class Context:
    def __init__(self):
        self.evaluations = []; self.events = []

    def evaluate(self, genome, fn, label=""):
        result = fn()
        assert np.isfinite(result["fitness"])
        assert np.isfinite(result["descriptor"]).all()
        self.evaluations.append((genome, result, label))
        return result

    def record(self, event):
        self.events.append(event)


def test_known_xor_controller_is_executed():
    first = np.zeros((3, 4)); first[:, 0] = [10, 10, -5]; first[:, 1] = [10, 10, -15]
    second = np.array([10, -10, 0, 0, -10.])
    result = evaluate_controller(np.r_[first.ravel(), second], "xor", 0)
    assert result["metrics"]["accuracy"] == 1.
    assert result["metrics"]["mse"] < 1e-6


def test_navigation_wall_blocks_direct_route_but_allows_detour():
    blocked = evaluate_policy(lambda x: [1, 0], "navigation", 2)
    def detour(x):
        if x[0] < .52:
            return [0, 1] if x[1] < .85 else [1, 0]
        return [1 if x[0] < .88 else 0, -1 if x[1] > .52 else 0]
    successful = evaluate_policy(detour, "navigation", 2)
    assert blocked["descriptor"][0] < .5
    assert blocked["metrics"]["collisions"] > 0
    assert successful["metrics"]["success"]


def test_behavioral_neighbors_and_local_competition():
    novelty, competition = novelty_and_competition([[0., 0.], [1., 0.], [4., 0.]], [2., 1., 3.], [], k=1)
    assert novelty.tolist() == [1., 1., 3.]
    assert competition.tolist() == [1., 0., 1.]
    order = pareto_order([[1., 1.], [2., 2.], [3., .5]])
    assert order[-1] == 0  # dominated by individual 1


@pytest.mark.parametrize("method", [method for method in METHODS if method != "fixed_controller"])
def test_search_step_pickle_resume_and_measured_replay(method):
    engine = SearchEngine({"method": method, "seed": 7, "population_size": 6, "generations": 2})
    context = Context(); engine.step(context)
    resumed = pickle.loads(pickle.dumps(engine))
    context2 = Context(); engine.step(context); resumed.step(context2)
    assert engine.done and resumed.done
    assert len(context.evaluations) == 12
    assert engine.summary() == resumed.summary()
    assert engine.replay()["fitness"] == pytest.approx(engine.best_result["fitness"], abs=1e-12)
    if method == "map_elites":
        assert engine.summary()["archive_size"] > 0
        assert all(str(parent[0]).startswith("archive:") for parent in context.events[-1]["parents"])
    if method == "nsga2":
        scores = np.array(engine.summary()["pareto_objectives"])
        for index, score in enumerate(scores):
            assert not any(np.all(other >= score) and np.any(other > score)
                           for j, other in enumerate(scores) if j != index)


def test_es_uses_antithetic_samples_and_changes_mean():
    engine = SearchEngine({"method": "es", "seed": 2, "population_size": 6, "generations": 1})
    before = engine.mean.copy(); context = Context(); engine.step(context)
    np.testing.assert_allclose(engine.population[:3]+engine.population[3:], np.tile(2*before, (3, 1)), atol=1e-14)
    assert not np.array_equal(engine.mean, before)
    assert context.events[0]["gradient_norm"] > 0


def test_controller_control_tasks_are_reproducible():
    for target in ("cartpole", "navigation"):
        weights = np.random.default_rng(3).normal(size=parameter_count(target))
        assert evaluate_controller(weights, target, 4) == evaluate_controller(weights, target, 4)
        assert evaluate_controller(weights, target, 4)["constraints"]


def test_cma_adapts_mean_covariance_and_step_size_from_actual_neural_fitness():
    engine = SearchEngine({"method": "cma_es", "seed": 4, "population_size": 8, "generations": 1})
    mean = engine.optimizer.mean.copy(); covariance = engine.optimizer.C.copy(); sigma = engine.optimizer.sigma
    engine.step(Context())
    assert not np.allclose(engine.optimizer.mean, mean)
    assert not np.allclose(engine.optimizer.C, covariance)
    assert engine.optimizer.sigma != sigma


def test_map_elites_replacement_and_offspring_from_retained_elite():
    engine = SearchEngine({"method": "map_elites", "seed": 3, "population_size": 4, "generations": 1})
    archive = engine.qd_archive
    first = np.zeros(engine.dimension); winner = np.ones(engine.dimension); rejected = np.full(engine.dimension, 2.)
    status = archive.add([first], [.1], [[.2, .2]])
    assert int(status["status"][0]) == 2
    status = archive.add([winner], [.2], [[.2, .2]])
    assert int(status["status"][0]) == 1
    status = archive.add([rejected], [.15], [[.2, .2]])
    assert int(status["status"][0]) == 0
    np.testing.assert_array_equal(archive.data("solution"), [winner])
    context = Context(); engine.step(context)
    assert all(parent == context.events[0]["parents"][0] for parent in context.events[0]["parents"])
    assert context.events[0]["parents"][0][0].startswith("archive:")
    assert not np.array_equal(engine.population[0], winner)


def test_nslc_reproduction_preserves_novel_local_tradeoff_not_top_fitness_only():
    class ControlledBehaviorContext(Context):
        """Controlled evaluator fixture to isolate selection, not acceptance evidence."""
        def evaluate(self, genome, fn, label=""):
            result = fn()
            index = int(label.rsplit(":", 1)[1])
            result.update(fitness=[100., 90., 80., 0.][index],
                          descriptor=[[0., 0.], [.1, 0.], [.2, 0.], [2., 0.]][index])
            self.evaluations.append((genome, result, label)); return result
    engine = SearchEngine({"method": "nslc", "seed": 7, "population_size": 4, "generations": 2,
                           "parameters": {"neighbors": 1, "archive_parent_probability": 0.}})
    context = ControlledBehaviorContext(); engine.step(context)
    selected = {int(parent.split(":")[1]) for parents in engine.parents for parent in parents}
    # 0 wins local fitness; 3 is much more novel despite worst absolute fitness.
    assert selected == {0, 3}
    assert context.events[0]["local_competition"] == [1., 0., 0., 0.]


@pytest.mark.parametrize("method", ["novelty", "nslc"])
def test_retained_novel_genotype_can_parent_after_current_population_is_replaced(method):
    engine = SearchEngine({"method": method, "seed": 3, "population_size": 4, "generations": 2,
                           "parameters": {"archive_parent_probability": 1., "mutation_rate": 0.}})
    engine.step(Context())
    retained = engine.archive[0]
    engine.archive = [retained]
    engine.population[:] = 99.  # all current candidates are different from the archive
    engine._reproduce(np.arange(4))
    for child, parents in zip(engine.population[1:], engine.parents[1:]):
        np.testing.assert_array_equal(child, retained[2])
        assert parents == [retained[3], retained[3]]


def test_fixed_controller_evaluates_exactly_one_unmodified_initial_network():
    engine = SearchEngine({"method": "fixed_controller", "seed": 7, "population_size": 8, "generations": 12})
    initial = engine.population[0].copy()
    context = Context(); engine.step(context); engine.step(context)
    assert engine.done and len(context.evaluations) == 1
    np.testing.assert_array_equal(engine.best, initial)
    assert engine.replay()["fitness"] == pytest.approx(engine.best_result["fitness"], abs=1e-12)
