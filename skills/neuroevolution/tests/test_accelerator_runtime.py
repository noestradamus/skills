"""Dispatch/cache invariants and real device RNG checks, including optional hardware."""
import json
import numpy as np
import pytest
import torch
from neuroevolution_lab.config import ExperimentSpec
from neuroevolution_lab.compatibility import validate_compatibility
from neuroevolution_lab.devices import resolve_device,synchronize,memory_stats
from neuroevolution_lab.runtime import Context,BudgetExceeded,rng_state,restore_rng


def spec(**kwargs):
    return ExperimentSpec(method="ga",target="xor",population_size=4,generations=1,**kwargs)


def test_batch_dispatches_before_computation_and_reuses_partial_cache(tmp_path):
    s=spec(); ctx=Context(tmp_path,s)
    first=ctx.evaluate([1],lambda:{"fitness":1.},label="a")
    ctx=Context(tmp_path,s)
    called=[]
    def kernel(indices):
        called.append(indices)
        assert ctx.eval_count==3
        assert len(ctx.results)==1
        return [{"fitness":float(i+1)} for i in indices]
    output=ctx.evaluate_batch([[1],[2],[3]],kernel,labels=["a","b","c"])
    assert called==[[1,2]] and output[0]==first
    assert [r["fitness"] for r in output]==[1,2,3]
    assert ctx.cursor==3
    ctx=Context(tmp_path,s)
    assert ctx.evaluate_batch([[1],[2],[3]],lambda _:pytest.fail("recomputed"),labels=["a","b","c"])==output
    with pytest.raises(RuntimeError,match="Non-reproducible"):
        Context(tmp_path,s).evaluate_batch([[99]],kernel,labels=["a"])


def test_batch_only_dispatches_affordable_candidates(tmp_path):
    s=spec(budget={"max_evaluations":2}); ctx=Context(tmp_path,s); called=[]
    def kernel(indices):
        called.extend(indices)
        return [{"fitness":float(i)} for i in indices]
    with pytest.raises(BudgetExceeded): ctx.evaluate_batch([1,2,3],kernel)
    assert called==[0,1] and ctx.eval_count==2 and len(ctx.results)==2
    with pytest.raises(BudgetExceeded):
        Context(tmp_path,s).evaluate_batch([1,2,3],lambda _:pytest.fail("repeated completed work"))


def test_batch_kernel_failure_charges_all_dispatched_candidates(tmp_path):
    ctx=Context(tmp_path,spec())
    def kernel(_): raise ValueError("device kernel failed")
    with pytest.raises(ValueError,match="kernel failed"): ctx.evaluate_batch([1,2],kernel)
    assert ctx.eval_count==2 and all(r["status"]=="failed" for r in ctx.results.values())


def test_invalid_batch_result_preserves_other_measured_results(tmp_path):
    ctx=Context(tmp_path,spec())
    with pytest.raises(ValueError):
        ctx.evaluate_batch([1,2],lambda _:[{"fitness":float("nan")},{"fitness":2.}])
    assert ctx.results[0]["status"]=="failed" and ctx.results[1]["result"]["fitness"]==2.
    assert len([r for r in ctx.rows if r["event"]=="batch_finished"])==1


def test_batch_interruption_retains_dispatched_identity(tmp_path):
    ctx=Context(tmp_path,spec())
    def interrupt(_): raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt): ctx.evaluate_batch([1,2],interrupt)
    assert ctx.eval_count==2 and not ctx.results
    resumed=Context(tmp_path,spec())
    resumed.evaluate_batch([1,2],lambda ix:[{"fitness":float(i)} for i in ix])
    assert resumed.eval_count==2 and len(resumed.results)==2


def test_device_choice_is_explicit_and_unsupported_composition_rejected(monkeypatch):
    with pytest.raises(ValueError,match="reference backend"):
        validate_compatibility(spec(compute={"device":"cuda"}))
    with pytest.raises(ValueError,match="no local torch"):
        validate_compatibility(ExperimentSpec(method="poet",target="terrain-tracking",compute={"backend":"torch"}))
    monkeypatch.setattr(torch.cuda,"is_available",lambda:False)
    with pytest.raises(ValueError,match="CUDA was requested"):
        resolve_device({"device":"cuda"})
    monkeypatch.setattr(torch.backends.mps,"is_available",lambda:True)
    monkeypatch.setenv("PYTORCH_ENABLE_MPS_FALLBACK","1")
    with pytest.raises(ValueError,match="Unset"):
        resolve_device({"device":"mps"})


@pytest.mark.parametrize("name",["cpu","mps","cuda"])
def test_actual_device_rng_restore_and_synchronized_batch(tmp_path,name):
    if name=="mps" and not torch.backends.mps.is_available(): pytest.skip("MPS hardware unavailable")
    if name=="cuda" and not torch.cuda.is_available(): pytest.skip("CUDA hardware unavailable")
    device=resolve_device({"device":name})
    before=rng_state(device)
    try:
        expected=torch.rand(24,device=device)
        restore_rng(before)
        actual=torch.rand(24,device=device)
        synchronize(device)
        assert torch.equal(actual,expected)
        assert actual.device.type==name
        ctx=Context(tmp_path,spec(compute={"backend":"torch","device":name}))
        def kernel(indices):
            x=torch.tensor([[i,1.] for i in indices],device=device)
            values=(x*x).sum(1).cpu().tolist()
            return [{"fitness":v} for v in values]
        values=ctx.evaluate_batch([0,1,2],kernel)
        assert [v["fitness"] for v in values]==[1,2,5]
        event=next(r for r in ctx.rows if r["event"]=="batch_finished")
        assert event["synchronized_seconds"]>0 and event["device"].startswith(name)
        json.dumps(memory_stats(device),allow_nan=False)
    finally:
        restore_rng(before)


def test_legacy_cpu_rng_tuple_remains_readable():
    old=rng_state()[:3]; restore_rng(old)
    np.testing.assert_array_equal(torch.get_rng_state().numpy(),old[2].numpy())


def test_environment_records_active_lock_without_mislabeling_external_install(monkeypatch):
    import sys
    from pathlib import Path
    import neuroevolution_lab.runtime as runtime
    root=Path(runtime.__file__).resolve().parents[2]
    monkeypatch.setattr(sys,"prefix",str(root/".venv"))
    default=runtime.environment_identity()
    assert default["active_environment"]=="default"
    assert default["lock_sha256"]==default["dependency_locks"]["default"]["sha256"]
    # The CPU Linux validation image intentionally has no optional CUDA bundle.
    if (root/"environments/cuda/uv.lock").exists():
        monkeypatch.setattr(sys,"prefix",str(root/"environments/cuda/.venv"))
        cuda=runtime.environment_identity()
        assert cuda["active_environment"]=="cuda"
        assert cuda["lock_sha256"]==cuda["dependency_locks"]["cuda"]["sha256"]
        assert cuda["lock_sha256"]!=default["lock_sha256"]
    monkeypatch.setattr(sys,"prefix","/external/test-environment")
    external=runtime.environment_identity()
    assert external["active_environment"] is None and external["lock_sha256"] is None
