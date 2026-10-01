"""Independent reference comparisons for actual population tensor execution."""
import copy
import json
import pickle

import numpy as np
import pytest
import torch

from neuroevolution_lab.accelerator_learning import (
    batched_lm_logits, lm_population_results, refine_sine_population,
)
from neuroevolution_lab.learning import (
    DifferentiableQD, ERL, EvolvedPlasticity, EvolutionaryInitialization,
    GradientRefinement, make_mlp, refine_sine, vector,
)
from neuroevolution_lab.models import (
    ModelMerging, ParameterEvolution, TinyAutoregressiveLM,
    arithmetic_sequences, evaluate_state,
)


@pytest.fixture(autouse=True)
def single_thread():
    prior = torch.get_num_threads()
    torch.set_num_threads(1)
    yield
    torch.set_num_threads(prior)


@pytest.fixture(params=["cpu", "mps", "cuda"])
def device(request):
    if request.param == "mps" and not torch.backends.mps.is_available():
        pytest.skip("MPS hardware/runtime unavailable")
    if request.param == "cuda" and not torch.cuda.is_available():
        pytest.skip("CUDA hardware/runtime unavailable")
    return request.param


class Context:
    def __init__(self, cached=None):
        self.records, self.events, self.batch_calls = [], [], []
        self.cached = cached or {}

    def evaluate(self, genome, fn, *, label=""):
        result = copy.deepcopy(self.cached[label]) if label in self.cached else fn()
        json.dumps(result, allow_nan=False)
        self.records.append((label, result))
        return result

    def evaluate_batch(self, genomes, fn, *, labels=None):
        indices = [i for i, label in enumerate(labels) if label not in self.cached]
        self.batch_calls.append(indices)
        results = dict(zip(indices, fn(indices))) if indices else {}
        return [self.evaluate(genome, lambda j=i: results[j], label=labels[i]) for i, genome in enumerate(genomes)]

    def record(self, event):
        json.dumps(event, allow_nan=False)
        self.events.append(copy.deepcopy(event))


def spec(method, target, device="cpu", backend="torch", **updates):
    result = {"method": method, "target": target, "seed": 8, "population_size": 3,
              "generations": 2, "parameters": {}, "learning": {"inner_steps": 3},
              "compute": {"device": device, "backend": backend, "batch_size": 2}}
    result.update(updates)
    return result


def test_population_refinement_matches_independent_sgd_and_per_model_clipping():
    weights = np.stack([vector(make_mlp(1, 6, 1, i)) for i in range(4)])
    weights[-1, -1] = 100.  # force clipping of only this candidate's gradient
    batched, records = refine_sine_population(weights, 6, (1.2, .1), 22, 23, 5, .03)
    for i, genome in enumerate(weights):
        reference, metrics = refine_sine(genome, 6, (1.2, .1), 22, 23, 5, .03)
        np.testing.assert_allclose(batched[i], reference, rtol=2e-5, atol=2e-6)
        assert records[i]["query_mse"] == pytest.approx(metrics["query_mse"], rel=2e-6)
    independent, _ = refine_sine_population(weights[:1], 6, (1.2, .1), 22, 23, 5, .03)
    np.testing.assert_allclose(independent[0], batched[0], atol=2e-6)


@pytest.mark.parametrize("inheritance", ["none", "baldwinian", "lamarckian"])
def test_batched_inheritance_reference_agreement_and_cached_subset(inheritance):
    config = spec("gradient_refinement", "sine_regression", learning={"inheritance": inheritance, "inner_steps": 5})
    live, reference = GradientRefinement(config), GradientRefinement({**config, "compute": {"backend": "reference"}})
    original, saved = live.population.copy(), pickle.dumps(live)
    ctx, ref_ctx = Context(), Context()
    live.step(ctx)
    reference.step(ref_ctx)
    np.testing.assert_allclose(live.population, reference.population, atol=2e-6)
    np.testing.assert_allclose([r["fitness"] for _, r in ctx.records], [r["fitness"] for _, r in ref_ctx.records], atol=2e-6)
    learned = np.asarray([r["metrics"]["learned_weights"] for _, r in ctx.records])
    expected = learned if inheritance == "lamarckian" else original
    np.testing.assert_allclose(live.last_inherited, expected)
    assert np.linalg.norm(learned-original) > .001 if inheritance != "none" else np.array_equal(learned, original)
    resumed = pickle.loads(saved)
    partial = Context(cached=dict(ctx.records[::2]))
    resumed.step(partial)
    assert partial.batch_calls == [[1], []]
    np.testing.assert_allclose(resumed.population, live.population, atol=2e-6)
    assert live.replay()["metrics"]["gradient_steps_during_replay"] == 0


def test_initialization_population_batch_preserves_task_reset():
    cfg = spec("evolutionary_initialization", "sine_task_family", parameters={"train_tasks": 2})
    live, reference = EvolutionaryInitialization(cfg), EvolutionaryInitialization({**cfg, "compute": {"backend": "reference"}})
    original = live.population.copy()
    ctx, baseline = Context(), Context()
    live.step(ctx)
    reference.step(baseline)
    np.testing.assert_array_equal(live.last_inherited, original)
    np.testing.assert_allclose([r["fitness"] for _, r in ctx.records], [r["fitness"] for _, r in baseline.records], atol=2e-6)
    assert all(len(r["metrics"]["per_task"]) == 2 for _, r in ctx.records)


def test_batched_gru_equations_match_pytorch_forward_and_exact_evaluation(device):
    models = [TinyAutoregressiveLM(6, i) for i in range(3)]
    states = {name: torch.stack([m.state_dict()[name] for m in models]).to(device) for name in models[0].state_dict()}
    data = arithmetic_sequences(31)["validation"].to(device)
    logits = batched_lm_logits(states, data[:, :-1])
    records = lm_population_results(states, data)
    for i, model in enumerate(models):
        torch.testing.assert_close(logits[i].cpu(), model(data[:, :-1].cpu()), atol=2e-5, rtol=2e-4)
        measured = evaluate_state(model.state_dict(), 6, data.cpu())
        assert records[i]["fitness"] == pytest.approx(measured["fitness"], abs=2e-5)
        assert records[i]["metrics"]["tensor_hash"] == measured["metrics"]["tensor_hash"]


@pytest.mark.parametrize("kind", ["merge", "adapter", "full"])
def test_model_population_evaluation_matches_individual_tensors(kind, device):
    cls = ModelMerging if kind == "merge" else ParameterEvolution
    parameters = {"hidden": 6, **({"mode": kind} if kind != "merge" else {})}
    engine = cls(spec(cls.method, "tiny_autoregressive", device, parameters=parameters))
    ctx = Context()
    engine._prepare(ctx)
    states = engine._batch_states(engine.population)
    for i, genome in enumerate(engine.population):
        for name, value in engine._state(genome).items():
            torch.testing.assert_close(states[name][i], value, atol=2e-7, rtol=2e-6)
    batch = engine._batch_results(list(range(engine.population_size)))
    scalar = [evaluate_state(engine._state(g), engine.hidden, engine.data["validation"]) for g in engine.population]
    np.testing.assert_allclose([r["fitness"] for r in batch], [r["fitness"] for r in scalar], atol=2e-5)
    assert all(r["tensor_delta_l2"] > 0 for r in engine.training_records)
    engine.step(ctx)
    assert ctx.batch_calls == [[0, 1], [0]]
    assert np.isfinite(engine.replay()["fitness"])


def test_actual_device_learning_and_batched_model_execution(device, monkeypatch):
    import neuroevolution_lab.accelerator_learning as kernels
    observed = []
    original = kernels.sine_population_forward
    def checked_forward(weights, inputs, hidden):
        observed.append(weights.device.type)
        return original(weights, inputs, hidden)
    monkeypatch.setattr(kernels, "sine_population_forward", checked_forward)
    refinement = GradientRefinement(spec("gradient_refinement", "sine_regression", device))
    reference = GradientRefinement(spec("gradient_refinement", "sine_regression", backend="reference"))
    ctx, baseline = Context(), Context()
    refinement.step(ctx)
    reference.step(baseline)
    assert set(observed) == {device}
    assert refinement.gradient_steps == 9
    np.testing.assert_allclose([r["fitness"] for _, r in ctx.records], [r["fitness"] for _, r in baseline.records], rtol=2e-4, atol=2e-5)
    merging = ModelMerging(spec("model_merging", "tiny_autoregressive", device, parameters={"hidden": 6}))
    merging.step(Context())
    assert all(t.device.type == device for s in merging.sources for t in s.values())
    assert all(t.device.type == device for t in merging._batch_states(merging.population).values())
    assert all(r["tensor_delta_l2"] > 0 for r in merging.training_records)
    assert np.isfinite(merging.replay()["fitness"])


def test_actual_device_sequential_learning_profiles(device):
    erl = ERL(spec("erl", "tracking_control", device, parameters={"horizon": 4},
                   learning={"batch_size": 4, "inner_steps": 2}))
    before = vector(erl.actor)
    erl.step(Context())
    assert next(erl.actor.parameters()).device.type == device
    assert next(erl.critic.parameters()).device.type == device
    assert np.linalg.norm(vector(erl.actor)-before) > 0
    np.testing.assert_array_equal(erl.population[-1], vector(erl.actor))
    assert len(erl.replay_buffer) == 16 and erl.gradient_updates == 2
    plasticity = EvolvedPlasticity(spec("evolved_plasticity", "associative_memory", device,
                                       parameters={"episodes": 1, "cues": 2}))
    plasticity.step(Context())
    assert plasticity.lifetime_updates == 24
    dqd = DifferentiableQD(spec("differentiable_qd", "differentiable_arm", device, population_size=8))
    dqd.step(Context())
    assert dqd.jacobian_evaluations > 0
    assert dqd.replay()["metrics"]["archive_consistent"]
    assert dqd.summary()["gradient_dtype"] == ("float32" if device == "mps" else "float64")


def test_historical_engine_without_compute_replays_as_cpu_reference():
    cfg = spec("gradient_refinement", "sine_regression")
    del cfg["compute"]
    engine = GradientRefinement(cfg)
    engine.step(Context())
    saved = pickle.loads(pickle.dumps(engine))
    assert saved.backend == "reference" and saved.device.type == "cpu"
    assert saved.replay() == engine.replay()


@pytest.mark.parametrize("method,target", [("gradient_refinement", "sine_regression"),
                                           ("model_merging", "tiny_autoregressive"),
                                           ("parameter_evolution", "tiny_autoregressive"),
                                           ("erl", "tracking_control")])
def test_actual_runtime_accelerator_checkpoint_resume_and_cached_batch(method, target, device, tmp_path, monkeypatch):
    from neuroevolution_lab.config import ExperimentSpec
    from neuroevolution_lab.runtime import Context as RuntimeContext, execute, load_checkpoint, read_events, resume_run
    # Report rendering is independent of this runtime/kernel/checkpoint test.
    monkeypatch.setattr("neuroevolution_lab.reporting.report", lambda path: {"report": str(path / "report.md")})
    config = ExperimentSpec.model_validate(spec(method, target, device, population_size=4,
        parameters={"hidden": 6, "horizon": 4}, learning={"inner_steps": 2, "batch_size": 4},
        budget={"max_evaluations": 16, "wall_seconds": 120}))
    clean_path, resumed_path = tmp_path / "clean", tmp_path / "resumed"
    clean = execute(config, clean_path)
    assert clean["status"] == "completed", clean
    evaluations_per_generation = 5 if method == "erl" else 4
    finished = 0
    original_record = RuntimeContext.record
    def interrupt_after_first_result_of_next_generation(context, event):
        nonlocal finished
        original_record(context, event)
        if event.get("event") == "evaluation_finished":
            finished += 1
            if finished == evaluations_per_generation + 1:
                # Inside a batched result commit, or a serial ERL evaluation.
                # The preceding full generation already has a checkpoint.
                raise KeyboardInterrupt("simulated partial-generation interruption")
    monkeypatch.setattr(RuntimeContext, "record", interrupt_after_first_result_of_next_generation)
    interrupted = execute(config, resumed_path)
    assert interrupted["status"] == "interrupted", interrupted
    partial = load_checkpoint(resumed_path)
    assert partial["engine"].generation == 1
    interrupted_dispatches = {r["id"]: r for r in read_events(resumed_path / "events.jsonl")
                              if r["event"] == "evaluation_started"}
    monkeypatch.setattr(RuntimeContext, "record", original_record)
    resumed = resume_run(resumed_path)
    assert resumed["status"] == "completed", resumed
    assert resumed["evaluations"] == clean["evaluations"] == 2*evaluations_per_generation
    restored, original = load_checkpoint(resumed_path), load_checkpoint(clean_path)
    engine, baseline = restored["engine"], original["engine"]
    np.testing.assert_allclose(engine.population, baseline.population, rtol=2e-4, atol=5e-5)
    assert engine.best_fitness == pytest.approx(baseline.best_fitness, rel=2e-4, abs=5e-5)
    assert engine.device.type == device
    if method in {"model_merging", "parameter_evolution"}:
        assert all(t.device.type == device for state in engine.sources for t in state.values())
        # These exact tensors were already trained and checkpointed before the
        # interruption. Resume must preserve their bytes, not retrain sources.
        for resumed_source, checkpoint_source in zip(engine.sources, partial["engine"].sources):
            assert resumed_source.keys() == checkpoint_source.keys()
            for name in resumed_source:
                torch.testing.assert_close(resumed_source[name], checkpoint_source[name], atol=0, rtol=0)
        for a, b in zip(engine.sources, baseline.sources):
            for name in a:
                # Separately trained accelerator baselines may differ in last
                # bits from parallel floating-point reductions. This is not a
                # checkpoint error; source hashes correctly expose that change.
                tolerance = 0 if device == "cpu" else 2e-6
                torch.testing.assert_close(a[name], b[name], atol=tolerance, rtol=tolerance)
    if method == "erl":
        assert next(engine.actor.parameters()).device.type == device
        np.testing.assert_allclose(vector(engine.actor), vector(baseline.actor), atol=5e-5, rtol=2e-4)
        assert engine.replay_sources == baseline.replay_sources
        assert engine.gradient_updates == baseline.gradient_updates
        assert engine.actor_optimizer.state_dict()["state"].keys() == baseline.actor_optimizer.state_dict()["state"].keys()
    rows = read_events(resumed_path / "events.jsonl")
    assert len([r for r in rows if r["event"] == "evaluation_started"]) == 2*evaluations_per_generation
    assert len([r for r in rows if r["event"] == "evaluation_finished"]) == 2*evaluations_per_generation
    resumed_dispatches = {r["id"]: r for r in rows if r["event"] == "evaluation_started"}
    for identity, saved_dispatch in interrupted_dispatches.items():
        # In the SAME run, preserve the whole original dispatch record exactly:
        # digest, source/base hashes, genome, labels and budget identity.
        assert resumed_dispatches[identity] == saved_dispatch
    clean_rows = read_events(clean_path / "events.jsonl")
    clean_dispatches = [r for r in clean_rows if r["event"] == "evaluation_started"]
    if device == "cpu":
        assert [r["digest"] for r in resumed_dispatches.values()] == [r["digest"] for r in clean_dispatches]
    else:
        for resumed_dispatch, clean_dispatch in zip(resumed_dispatches.values(), clean_dispatches):
            assert (resumed_dispatch["id"], resumed_dispatch["label"], resumed_dispatch["kind"]) == (
                clean_dispatch["id"], clean_dispatch["label"], clean_dispatch["kind"])
            a, b = resumed_dispatch["genome"], clean_dispatch["genome"]
            assert a.keys() == b.keys()
            for key in a:
                if key in {"source_hashes", "base_hash"}:
                    # Sources from two independent training executions have
                    # been compared numerically above; their hashes may differ.
                    continue
                if isinstance(a[key], list):
                    np.testing.assert_allclose(a[key], b[key], rtol=2e-4, atol=5e-5)
                else:
                    assert a[key] == b[key]
    # Engine NumPy state and applicable global accelerator state survive pickle.
    assert engine.rng.bit_generator.state == baseline.rng.bit_generator.state
    torch.testing.assert_close(restored["rng"][2], original["rng"][2], atol=0, rtol=0)
    if device != "cpu":
        assert restored["rng"][3]["device"].startswith(device)
        torch.testing.assert_close(restored["rng"][3]["state"], original["rng"][3]["state"], atol=0, rtol=0)
