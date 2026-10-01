"""Mechanism-level tests rather than claims that a short run must solve a task."""
import json
import pickle

import numpy as np
import pytest

from neuroevolution_lab.ecology import (
    METHODS, TARGETS, CompetitiveEngine, CooperativeEngine, PoetEngine,
    RewardSurrogate, SurrogateEngine, competitive_match, competitive_panel,
    cooperative_episode, cycling_diagnostic, fixed_opponents, network_size,
    prescription_episode, prescription_reward, terrain_episode,
)


class RecordingContext:
    def __init__(self):
        self.evaluations = []
        self.events = []

    def evaluate(self, genome, fn, *, label="", kind="observed"):
        result = fn()
        assert np.isfinite(result["fitness"])
        json.dumps(result, allow_nan=False)
        self.evaluations.append({"genome": genome, "label": label, "kind": kind, "result": result})
        return result

    def record(self, event):
        json.dumps(event, allow_nan=False)
        self.events.append(event)


def spec(method, **parameters):
    return {"method": method, "target": TARGETS[method][0], "seed": 23,
            "population_size": 6, "generations": 3, "parameters": parameters, "learning": {}}


def run_engine(engine):
    context = RecordingContext()
    while not engine.done:
        engine.step(context)
    return context


def test_cooperative_fitness_changes_when_only_partner_changes():
    focal = np.zeros(network_size(5))
    partner_a = np.zeros_like(focal)
    partner_b = np.zeros_like(focal)
    partner_b[-1] = 2.0
    first = cooperative_episode([focal, partner_a])
    second = cooperative_episode([focal, partner_b])
    assert first["fitness"] != pytest.approx(second["fitness"])


def test_cooperative_credit_is_team_fitness_and_saved_team_is_measured():
    engine = CooperativeEngine(spec("cooperative"))
    context = run_engine(engine)
    credits = [row for row in context.events if row["event"] == "cooperative_credit"]
    assert len(credits) == 2 * 6 * 3
    assert any(row["partner_dependence"] > 0.001 for row in credits)
    for row in credits:
        assert row["shared_fitness"] == pytest.approx(np.mean(row["partner_fitnesses"]))
    assert engine.replay()["fitness"] == pytest.approx(engine.best_fitness)
    assert len(engine.best_team) == 2


def test_cooperative_saves_stronger_team_measured_during_partner_trials():
    engine = CooperativeEngine({**spec("cooperative"), "seed": 3})
    context = run_engine(engine)
    best = max(context.evaluations, key=lambda row: row["result"]["fitness"])
    assembled = [row["result"]["fitness"] for row in context.evaluations
                 if row["label"].endswith("/assembled_team")]
    # A best team need not consist of the two best average-credit individuals.
    assert "/partner" in best["label"]
    assert best["result"]["fitness"] > max(assembled)
    assert engine.best_fitness == pytest.approx(best["result"]["fitness"])
    np.testing.assert_array_equal(engine.best_team.ravel(), best["genome"])
    assert engine.replay()["fitness"] == pytest.approx(best["result"]["fitness"])


def test_competitive_payoff_is_zero_sum_and_policies_interact():
    a, b, c = fixed_opponents()[:3]
    assert competitive_match(a, b)["fitness"] == pytest.approx(-competitive_match(b, a)["fitness"])
    assert competitive_match(a, b)["fitness"] < -0.9
    assert competitive_match(a, c)["fitness"] > 0.9
    assert competitive_match(a, a)["fitness"] == pytest.approx(0)


def test_competitive_archive_and_absolute_panel_do_not_confuse_relative_progress():
    engine = CompetitiveEngine(spec("competitive", archive_size=2))
    original_panel = engine.validation_panel.copy()
    context = run_engine(engine)
    assert len(engine.hall_of_fame) == 2
    assert [row["historical_opponents"] for row in engine.history] == [0, 1, 2]
    assert np.array_equal(original_panel, engine.validation_panel)
    other = CompetitiveEngine({**spec("competitive"), "seed": 999})
    assert np.array_equal(other.validation_panel, original_panel)
    assert engine.replay()["fitness"] == pytest.approx(engine.best_fitness)
    assert len([e for e in context.evaluations if "fixed_validation" in e["label"]]) == 3
    assert cycling_diagnostic({"relative_fitness": 0.1, "absolute_worst": -0.1},
                              {"relative_fitness": 0.2, "absolute_worst": -0.3})
    assert not cycling_diagnostic({"relative_fitness": 0.1, "absolute_worst": -0.1},
                                  {"relative_fitness": 0.2, "absolute_worst": -0.05})


def test_poet_environment_changes_actual_rollout():
    genome = np.zeros(network_size(5))
    easy = terrain_episode(genome, [0.1, 0.4, 0, 0.1])
    harder = terrain_episode(genome, [0.9, 1.8, 0.3, 0.25])
    assert easy["fitness"] > harder["fitness"]


def test_poet_admission_capacity_optimization_and_real_adapted_transfers():
    engine = PoetEngine(spec("poet", max_pairs=3, minimal_fitness=-10, maximal_fitness=1.01,
                             reproduction_threshold=-10, novelty_threshold=0.001))
    context = run_engine(engine)
    assert len(engine.pairs) <= 3
    assert len(engine.ancestry) >= 4
    assert all(row["parent"] is not None for row in engine.ancestry[1:])
    assert engine.transfer_attempts == engine.adapted_transfer_attempts > 0
    transfers = [row for row in context.events if row["event"] == "poet_transfer"]
    assert any(row["adaptation_distance"] > 0 for row in transfers)
    assert all(row["adapted_fitness"] >= row["direct_fitness"] for row in transfers)
    assert all(row["accepted"] == (max(row["direct_fitness"], row["adapted_fitness"]) > row["incumbent_fitness"])
               for row in transfers)
    optimizations = [row for row in context.events if row["event"] == "poet_policy_optimization"]
    assert any(row["gradient_norm"] > 0 for row in optimizations)
    assert all(row["after"] >= row["before"] for row in optimizations)
    assert engine.replay()["fitness"] == pytest.approx(engine.best_fitness)


@pytest.mark.parametrize("parameters,reason", [
    ({"novelty_threshold": 3.0}, "novel"),
    ({"minimal_fitness": 2.0, "maximal_fitness": 3.0}, "admissible"),
])
def test_poet_filters_reject_unsuitable_new_tasks(parameters, reason):
    engine = PoetEngine(spec("poet", reproduction_threshold=-10, **parameters))
    context = run_engine(engine)
    assert len(engine.ancestry) == 1
    filters = [row for row in context.events if row["event"] == "poet_environment_filter"]
    assert len(filters) == 3
    assert all(not row[reason] for row in filters)


def test_surrogate_learns_an_imperfect_context_action_predictor():
    rng = np.random.default_rng(42)
    inputs = rng.uniform(-1, 1, (12, 2))
    rewards = prescription_reward(inputs[:, 0], inputs[:, 1])
    model = RewardSurrogate(rng)
    before = model.output.copy()
    model.fit(inputs, rewards)
    assert not np.array_equal(model.output, before)
    test_inputs = rng.uniform(-1, 1, (50, 2))
    error = np.mean(np.abs(model.predict(test_inputs) - prescription_reward(test_inputs[:, 0], test_inputs[:, 1])))
    assert 0.001 < error < 2


def test_surrogate_rechecks_predictions_in_true_environment_before_saving_best():
    engine = SurrogateEngine(spec("surrogate", true_confirmations=1))
    context = run_engine(engine)
    predictions = [entry for entry in context.evaluations if entry["kind"] == "predicted"]
    confirmations = [entry for entry in context.evaluations if "/true/" in entry["label"]]
    assert len(predictions) == 18
    assert len(confirmations) == 6
    assert engine.true_policy_evaluations == 6
    assert engine.true_outcome_queries == 12 + 6 * 33
    assert engine.best_fitness == pytest.approx(max(row["result"]["fitness"] for row in confirmations))
    assert engine.replay()["fitness"] == pytest.approx(engine.best_fitness)
    assert all(row["confirmation_mae_before_refit"] > 0 for row in engine.history)
    assert all(sum(c["exploration"] for c in row["confirmation"]) == 1 for row in engine.history)


@pytest.mark.parametrize("method", list(METHODS))
def test_pickle_resume_preserves_full_search_state_and_rng(method):
    complete = METHODS[method](spec(method))
    complete_context = run_engine(complete)
    interrupted = METHODS[method](spec(method))
    context = RecordingContext()
    interrupted.step(context)
    resumed = pickle.loads(pickle.dumps(interrupted))
    while not resumed.done:
        resumed.step(context)
    assert resumed.summary() == complete.summary()
    assert context.evaluations == complete_context.evaluations
    assert resumed.replay(seed=123) == complete.replay(seed=123)


def test_unsupported_target_is_rejected():
    with pytest.raises(ValueError, match="supports targets"):
        CooperativeEngine({**spec("cooperative"), "target": "cartpole"})


@pytest.mark.parametrize("method,parameters", [
    ("cooperative", {"team_mode": "joint"}),
    ("competitive", {"archive_size": 0}),
    ("poet", {"transfer_mode": "none"}),
    ("poet", {"transfer_mode": "direct"}),
    ("surrogate", {"search_mode": "direct"}),
])
def test_baselines_are_real_evaluated_searches(method, parameters):
    engine = METHODS[method](spec(method, **parameters))
    context = run_engine(engine)
    assert engine.replay()["fitness"] == pytest.approx(engine.best_fitness)
    assert context.evaluations
    if method == "cooperative":
        assert len(context.evaluations) == 6 * 3
        assert all("joint_team" in row["label"] for row in context.evaluations)
    elif method == "competitive":
        assert not engine.hall_of_fame
        assert all(row["historical_opponents"] == 0 for row in engine.history)
    elif method == "poet":
        assert engine.adapted_transfer_attempts == 0
        assert (engine.transfer_attempts == 0) == (parameters["transfer_mode"] == "none")
    elif method == "surrogate":
        assert engine.predicted_evaluations == 0
        assert engine.true_policy_evaluations == 6 * 3
        assert engine.true_outcome_queries == 6 * 3 * 33


@pytest.mark.parametrize("method", list(METHODS))
def test_journal_resume_after_partial_generation_avoids_repeating_environment_work(method, tmp_path):
    from neuroevolution_lab.config import ExperimentSpec
    from neuroevolution_lab.runtime import Context

    specification = ExperimentSpec.model_validate({**spec(method), "budget": {"max_evaluations": 5000}})
    engine = METHODS[method](specification.model_dump())
    frozen_before_step = pickle.dumps(engine)
    first_context = Context(tmp_path, specification)
    original = first_context.evaluate
    function_calls = []

    def interrupted_evaluate(genome, fn, **kwargs):
        def counted():
            function_calls.append(kwargs["label"])
            return fn()
        result = original(genome, counted, **kwargs)
        if len(function_calls) == 5:
            raise KeyboardInterrupt("injected immediately after fifth persisted evaluation")
        return result

    first_context.evaluate = interrupted_evaluate
    with pytest.raises(KeyboardInterrupt):
        engine.step(first_context)
    engine = pickle.loads(frozen_before_step)
    resumed_context = Context(tmp_path, specification, cursor=0)
    resumed_original = resumed_context.evaluate

    def resumed_evaluate(genome, fn, **kwargs):
        def counted():
            function_calls.append(kwargs["label"])
            return fn()
        return resumed_original(genome, counted, **kwargs)

    resumed_context.evaluate = resumed_evaluate
    while not engine.done:
        engine.step(resumed_context)
    uninterrupted = METHODS[method](specification.model_dump())
    reference = run_engine(uninterrupted)
    assert engine.summary() == uninterrupted.summary()
    assert len(function_calls) == len(reference.evaluations)
    assert len(function_calls) == len(set(function_calls))
    assert resumed_context.eval_count == len(reference.evaluations)
