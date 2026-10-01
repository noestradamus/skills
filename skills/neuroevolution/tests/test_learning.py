"""Mechanism tests: acquired state, explicit gradients, replay, and real tensors."""
import copy
import json
import pickle

import numpy as np
import pytest
import torch

from neuroevolution_lab.learning import (
    METHODS as LEARNING_METHODS, DifferentiableQD, ERL, EvolutionaryInitialization,
    GradientRefinement, arm_values_and_jacobian, plastic_episode, plastic_genome_size,
    refine_sine, make_mlp, vector, tensor_digest,
)
from neuroevolution_lab.models import (
    METHODS as MODEL_METHODS, ModelMerging, ParameterEvolution, TinyAutoregressiveLM,
    adapter_state, arithmetic_sequences, merge_states, state_digest,
)


@pytest.fixture(autouse=True)
def single_thread():
    old = torch.get_num_threads()
    torch.set_num_threads(1)
    yield
    torch.set_num_threads(old)


class Context:
    def __init__(self, cache=None):
        self.events = []
        self.measurements = []
        self.cache = cache

    def evaluate(self, genome, fn, label=""):
        index = len(self.measurements)
        measurement = copy.deepcopy(self.cache[index]) if self.cache is not None else fn()
        assert np.isfinite(measurement["fitness"])
        # Evidence must survive the actual runtime's JSON journal.
        json.dumps(measurement, allow_nan=False)
        self.measurements.append(measurement)
        return measurement

    def record(self, event):
        json.dumps(event, allow_nan=False)
        self.events.append(copy.deepcopy(event))


def spec(method, target, **overrides):
    values = {"method": method, "target": target, "seed": 8, "population_size": 3,
              "generations": 2, "parameters": {}, "learning": {"inner_steps": 3}}
    values.update(overrides)
    return values


@pytest.mark.parametrize("mode", ["none", "baldwinian", "lamarckian"])
def test_inheritance_transmits_correct_weights(mode):
    engine = GradientRefinement(spec("gradient_refinement", "sine_regression",
                                learning={"inheritance": mode, "inner_steps": 6}))
    before = engine.population.copy()
    ctx = Context()
    engine.step(ctx)
    acquired = np.asarray([r["metrics"]["learned_weights"] for r in ctx.measurements])
    if mode == "none":
        np.testing.assert_array_equal(acquired, before)
        assert engine.gradient_steps == 0
    else:
        assert np.linalg.norm(acquired-before) > .001
        assert engine.gradient_steps == 18
    expected = acquired if mode == "lamarckian" else before
    np.testing.assert_allclose(engine.last_inherited, expected)
    inheritance=[e for e in ctx.events if e["event"]=="inheritance"]
    assert len(inheritance)==engine.population_size
    for event in inheritance:
        assert (event["transmitted_hash"] == event["learned_hash"]) == (mode != "baldwinian")
    lineage=next(e for e in ctx.events if e["event"]=="population_ancestry")
    assert len(lineage["parents"])==engine.population_size
    assert lineage["offspring_tensor_hashes_before_profile_projection"]==[tensor_digest(g) for g in engine.population]


def test_gradient_refinement_changes_network_function_and_decreases_training_task_loss():
    weights = vector(make_mlp(1, 8, 1, 4))
    learned, metrics = refine_sine(weights, 8, (1., 0.), 100, 101, 60, .03)
    assert metrics["parameter_delta_l2"] > .01
    assert metrics["query_mse"] < metrics["initial_query_mse"]
    assert not np.array_equal(weights, learned)


def test_refinement_replay_uses_saved_phenotype_without_retraining(monkeypatch):
    engine = GradientRefinement(spec("gradient_refinement", "sine_regression"))
    engine.step(Context())
    def forbidden(*args, **kwargs):
        raise AssertionError("frozen-controller replay must not retrain")
    monkeypatch.setattr("neuroevolution_lab.learning.refine_sine", forbidden)
    replay = engine.replay()
    assert replay["metrics"]["gradient_steps_during_replay"] == 0
    assert replay["metrics"]["replay_kind"] == "frozen_selected_phenotype"


def test_meta_initialization_evaluates_adaptation_on_disjoint_tasks():
    engine = EvolutionaryInitialization(spec("evolutionary_initialization", "sine_task_family"))
    ctx = Context()
    engine.step(ctx)
    result = engine.replay(seed=992)
    metrics = result["metrics"]
    assert set(metrics["train_task_ids"]).isdisjoint(metrics["test_task_ids"])
    assert all(m["parameter_delta_l2"] > 0 for m in metrics["per_task"])
    assert all(len(e["adapted_task_hashes"]) == len(engine.train_tasks) for e in ctx.events if e["event"]=="inheritance")
    assert all(r["metrics"]["selection_split"] == "training_tasks_query_sets" for r in ctx.measurements)
    colliding_rng = engine.replay(seed=engine.seed+731)
    assert set(engine.train_tasks).isdisjoint(tuple(r["task_parameters"]) for r in colliding_rng["metrics"]["per_task"])
    with pytest.raises(ValueError, match="inherits initial weights"):
        EvolutionaryInitialization(spec("evolutionary_initialization", "sine_task_family",
                                         learning={"inheritance": "lamarckian"}))


def known_associative_rule(cues):
    genome = np.zeros(plastic_genome_size(cues), dtype=np.float32)
    genome[cues:2*cues] = 2.  # A: pre*post association
    genome[5*cues:6*cues] = 1.  # positive synapse-specific rates
    genome[-2] = 10.  # neuromodulator observes feedback availability
    genome[-1] = -5.
    return genome


def test_plastic_rules_and_modulation_act_during_lifetime_not_on_learning_rate_only():
    genome = known_associative_rule(3)
    live = plastic_episode(genome, 3, 30)
    frozen = plastic_episode(genome, 3, 30, plastic=False)
    assert live["mse"] < .05
    assert frozen["mse"] == 1.
    assert live["weight_delta"] > 1.
    assert frozen["weight_delta"] == 0.
    assert live["modulation_max"] - live["modulation_min"] > .9
    # Reversing A reverses associative learning without altering eta.
    reverse = genome.copy()
    reverse[3:6] *= -1
    assert plastic_episode(reverse, 3, 30)["mse"] > 2.
    assert live["initial_weights"] == [0., 0., 0.]


def test_erl_population_and_rl_actor_share_experience_and_reinsert_learned_actor():
    engine = ERL(spec("erl", "tracking_control", parameters={"horizon": 10},
                      learning={"inner_steps": 3, "batch_size": 8}))
    actor_before = vector(engine.actor)
    ctx = Context()
    engine.step(ctx)
    assert engine.replay_sources == {"population": 30, "rl_actor": 10}
    assert len(engine.replay_buffer) == 40
    assert engine.gradient_updates == 3
    assert np.linalg.norm(vector(engine.actor)-actor_before) > 0.
    np.testing.assert_array_equal(engine.population[-1], vector(engine.actor))
    assert ctx.events[-1]["reinsertion_slot"] == 2
    assert ctx.events[-1]["actor_delta"] > 0


def test_erl_cached_evaluation_reconstructs_replay_identically():
    original = ERL(spec("erl", "tracking_control", learning={"inner_steps": 2, "batch_size": 8}))
    recovered = pickle.loads(pickle.dumps(original))
    first = Context()
    original.step(first)
    # ctx.evaluate may return journaled results without re-running the evaluator.
    second = Context(cache=first.measurements)
    recovered.step(second)
    np.testing.assert_array_equal(original.population, recovered.population)
    np.testing.assert_array_equal(vector(original.actor), vector(recovered.actor))
    assert original.replay_sources == recovered.replay_sources


@pytest.mark.parametrize("mode", ["evolution_only", "learning_only"])
def test_erl_pure_controls_have_no_hidden_hybrid_mechanism(mode):
    engine = ERL(spec("erl", "tracking_control", population_size=5,
                      parameters={"mode": mode, "horizon": 10}, learning={"inner_steps": 3, "batch_size": 8}))
    population_before = engine.population.copy()
    actor_before = vector(engine.actor)
    engine.step(Context())
    assert engine.summary()["environment_interactions"] == 50
    assert engine.reinsertions == 0
    if mode == "evolution_only":
        assert engine.gradient_updates == 0
        assert engine.replay_sources == {"population": 50, "rl_actor": 0}
        np.testing.assert_array_equal(actor_before, vector(engine.actor))
        assert not np.array_equal(population_before, engine.population)
    else:
        assert engine.gradient_updates == 3
        assert engine.replay_sources == {"population": 0, "rl_actor": 50}
        np.testing.assert_array_equal(population_before, engine.population)
        np.testing.assert_array_equal(engine.best_genome, vector(engine.actor))
        assert engine.best_fitness is None  # final updated actor has no claimed training score
    assert np.isfinite(engine.replay()["fitness"])


def test_dqd_objective_and_descriptor_gradients_match_finite_differences():
    x = np.array([.1, -.3, .6, -.2])
    _, jac = arm_values_and_jacobian(x)
    finite = np.empty_like(jac)
    for i in range(len(x)):
        delta = np.zeros(len(x)); delta[i] = 1e-6
        plus, _ = arm_values_and_jacobian(x+delta)
        minus, _ = arm_values_and_jacobian(x-delta)
        finite[:, i] = (plus-minus)/(2e-6)
    np.testing.assert_allclose(jac, finite, atol=1e-7)
    assert np.linalg.norm(jac[1:]) > 0.


def test_dqd_uses_gradients_and_preserves_correct_archive_cells():
    engine = DifferentiableQD(spec("differentiable_qd", "differentiable_arm", population_size=10))
    ctx = Context()
    engine.step(ctx)
    assert engine.jacobian_evaluations > 0
    assert any(e["event"] == "dqd_jacobian" for e in ctx.events)
    assert engine.replay()["metrics"]["archive_consistent"]
    assert "variant" in engine.summary()["algorithm"]
    assert "CMA-MEGA" in engine.summary()["not_implemented"]


def test_generated_lm_task_partitions_are_disjoint():
    data = arithmetic_sequences(33)
    sets = {k: {tuple(row) for row in value.tolist()} for k, value in data.items()}
    assert [len(sets[k]) for k in ("train", "validation", "test")] == [48, 16, 16]
    assert not (sets["train"] & sets["test"] or sets["train"] & sets["validation"] or sets["test"] & sets["validation"])
    identifiers = {k: {tuple(row[:3]) for row in value.tolist()} for k, value in data.items()}
    assert identifiers["train"].isdisjoint(identifiers["test"])


def test_aligned_merge_endpoints_and_rejection_of_wrong_tensor_shapes():
    a = TinyAutoregressiveLM(6, 1).state_dict()
    b = TinyAutoregressiveLM(6, 2).state_dict()
    assert state_digest(merge_states([a, b], np.zeros(3))) == state_digest(a)
    assert state_digest(merge_states([a, b], np.ones(3))) == state_digest(b)
    middle = merge_states([a, b], np.full(3, .5))
    for name in a:
        torch.testing.assert_close(middle[name], (a[name]+b[name])/2)
    with pytest.raises(ValueError, match="shape or dtype"):
        merge_states([a, TinyAutoregressiveLM(7).state_dict()], np.zeros(3))


def test_model_merging_trains_actual_source_tensors_and_scores_heldout_tokens():
    engine = ModelMerging(spec("model_merging", "tiny_autoregressive", parameters={"hidden": 6},
                               learning={"inner_steps": 8}))
    ctx = Context()
    engine.step(ctx)
    assert len(engine.sources) == 2
    assert all(state_digest(s) != engine.initial_hash for s in engine.sources)
    assert all(r["tensor_delta_l2"] > 0 for r in engine.training_records)
    assert all(r["final_train_loss"] < r["initial_train_loss"] for r in engine.training_records)
    assert any(e["event"] == "aligned_tensor_merge" for e in ctx.events)
    replay = engine.replay()
    assert replay["metrics"]["split"] == "heldout_tasks_and_sequences"
    assert replay["metrics"]["test_selection"] is False
    assert len(replay["metrics"]["source_test_losses"]) == 2


def test_low_rank_adapter_changes_only_output_tensor_and_leaves_base_untouched():
    base = TinyAutoregressiveLM(6).state_dict()
    before = state_digest(base)
    genes = np.ones(2*(6+12), dtype=np.float32)*.1
    adapted = adapter_state(base, genes, 6, 2)
    assert state_digest(base) == before
    assert not torch.equal(adapted["output.weight"], base["output.weight"])
    for name in base:
        if name != "output.weight":
            torch.testing.assert_close(adapted[name], base[name], rtol=0, atol=0)


@pytest.mark.parametrize("mode", ["adapter", "full"])
def test_parameter_evolution_evaluates_real_model_parameters(mode):
    engine = ParameterEvolution(spec("parameter_evolution", "tiny_autoregressive",
                                    parameters={"hidden": 6, "mode": mode}, learning={"inner_steps": 3}))
    ctx = Context()
    engine.step(ctx)
    events = [e for e in ctx.events if e["event"] == "lm_parameter_evaluation"]
    assert len({e["effective_tensor_hash"] for e in events}) > 1
    assert len({r["fitness"] for r in ctx.measurements}) > 1
    assert engine.summary()["base_frozen"] == (mode == "adapter")
    assert np.isfinite(engine.replay()["metrics"]["next_token_loss"])


@pytest.mark.parametrize("name,factory", list({**LEARNING_METHODS, **MODEL_METHODS}.items()))
def test_engine_checkpoint_replay_matches_continuous_run(name, factory):
    values = spec(name, factory.target, population_size=2, parameters={"hidden": 5}, learning={"inner_steps": 2})
    engine = factory(values)
    first = Context()
    engine.step(first)
    restored = pickle.loads(pickle.dumps(engine))
    a, b = Context(), Context()
    engine.step(a)
    restored.step(b)
    assert engine.done and restored.done
    assert engine.summary() == restored.summary()
    assert a.measurements == b.measurements
    assert engine.replay(seed=999) == restored.replay(seed=999)


def test_engine_rejects_misleading_target_name():
    with pytest.raises(ValueError, match="supports target"):
        GradientRefinement(spec("gradient_refinement", "hosted_llm_weights"))


def test_ablations_disable_the_declared_mechanism():
    dqd = DifferentiableQD(spec("differentiable_qd", "differentiable_arm",
                                parameters={"gradient_proposals": False}))
    dqd.step(Context())
    assert dqd.jacobian_evaluations == 0
    assert "control" in dqd.summary()["algorithm"]
    erl = ERL(spec("erl", "tracking_control", parameters={"rl_reinsertion": False},
                   learning={"inner_steps": 2, "batch_size": 8}))
    erl.step(Context())
    assert erl.gradient_updates == 2 and erl.reinsertions == 0
    assert erl.last_reinserted is None
    plastic = LEARNING_METHODS["evolved_plasticity"](spec("evolved_plasticity", "associative_memory",
                                                    parameters={"plasticity_enabled": False}))
    ctx = Context()
    plastic.step(ctx)
    assert all(r["metrics"]["weight_delta"] == 0 for r in ctx.measurements)
