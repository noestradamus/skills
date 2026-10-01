import json
from pathlib import Path
import pickle
import subprocess
import sys
import textwrap
import pytest
from neuroevolution_lab.config import ExperimentSpec,ModelAccess
from neuroevolution_lab.runtime import Context,BudgetExceeded,PendingModel,execute,resume_run,load_checkpoint,read_events,encoded
from neuroevolution_lab.providers import complete,next_request,submit_response
from neuroevolution_lab.compatibility import validate_compatibility

def spec(**kw):
    return ExperimentSpec(method="ga",target="xor",population_size=4,generations=2,**kw)

def test_failures_and_pending_are_charged_without_duplicate_dispatches(tmp_path):
    s=spec(budget={"max_evaluations":2})
    c=Context(tmp_path,s)
    def bad(): raise ValueError("candidate failure")
    with pytest.raises(ValueError): c.evaluate([1],bad)
    def wait(): raise PendingModel("waiting")
    with pytest.raises(PendingModel): c.evaluate([2],wait)
    assert c.eval_count==2
    assert c.evaluate([2],lambda:{"fitness":3})["fitness"]==3
    with pytest.raises(BudgetExceeded): c.evaluate([3],lambda:{"fitness":4})
    assert len([r for r in c.rows if r["event"]=="evaluation_started"])==2

def test_cached_evaluation_does_not_repeat_and_checks_identity(tmp_path):
    c=Context(tmp_path,spec())
    expected=c.evaluate([1],lambda:{"fitness":2.})
    c=Context(tmp_path,spec())
    assert c.evaluate([1],lambda:pytest.fail("repeated"))==expected
    c=Context(tmp_path,spec())
    with pytest.raises(RuntimeError,match="Non-reproducible"): c.evaluate([2],lambda:{"fitness":2.})

def test_interrupted_step_resumes_exactly_without_repeating_completed_evaluations(tmp_path,monkeypatch):
    import neuroevolution_lab.search as search
    original=search.evaluate_controller
    interrupted=[False]; count=[0]
    def evaluator(*args,**kwargs):
        count[0]+=1
        if count[0]==3 and not interrupted[0]:
            interrupted[0]=True; raise KeyboardInterrupt()
        return original(*args,**kwargs)
    monkeypatch.setattr(search,"evaluate_controller",evaluator)
    p=tmp_path/"resume"; result=execute(spec(),p)
    assert result["status"]=="interrupted"
    assert result["evaluations"]==3
    resumed=resume_run(p)
    assert resumed["status"]=="completed"
    assert count[0]==9  # eight measured candidates plus interrupted attempt
    clean=execute(spec(),tmp_path/"clean")
    assert encoded(resumed["summary"])==encoded(clean["summary"])
    assert len([r for r in read_events(p/"events.jsonl") if r.get("event")=="evaluation_started"])==8

def test_budget_recovery_retains_completed_measurements(tmp_path):
    s=spec(budget={"max_evaluations":3})
    a=execute(s,tmp_path)
    assert a["status"]=="budget_exhausted" and a["evaluations"]==3
    b=resume_run(tmp_path)
    assert b["evaluations"]==3 and b["status"]=="budget_exhausted"

def test_checkpoint_detects_corruption(tmp_path):
    execute(spec(),tmp_path)
    p=tmp_path/"checkpoint.pkl"; p.write_bytes(p.read_bytes()+b"bad")
    with pytest.raises(ValueError,match="checksum"): load_checkpoint(tmp_path)

def test_bridge_pending_submitted_cached_and_immutable(tmp_path):
    c=Context(tmp_path,spec(model={"provider":"bridge"}))
    messages=[{"role":"user","content":"a request"}]
    with pytest.raises(PendingModel): complete(c,messages,"key")
    r=next_request(tmp_path)
    assert r["status"]=="pending"
    submit_response(tmp_path,r["id"],'{"answer":1}',"protocol-test fixture; not live model")
    assert complete(c,messages,"key")=='{"answer":1}' and next_request(tmp_path) is None
    with pytest.raises(ValueError,match="immutable"): submit_response(tmp_path,r["id"],"different","test")

def test_hosted_spending_requires_explicit_limit_and_prices():
    with pytest.raises(ValueError): ModelAccess(provider="endpoint",base_url="https://example.com/v1")
    access=ModelAccess(provider="endpoint",base_url="http://localhost:9000/v1")
    assert access.max_cost_usd==0

def test_incompatible_composition_is_rejected():
    with pytest.raises(ValueError,match="does not support"): validate_compatibility(spec(learning={"steps":5}))
    with pytest.raises(ValueError,match="supports"): validate_compatibility(ExperimentSpec(method="neat",target="arithmetic_tools"))

def test_nonfinite_measurement_is_failed_and_charged(tmp_path):
    c=Context(tmp_path,spec())
    with pytest.raises(ValueError): c.evaluate([1],lambda:{"fitness":float("nan")})
    assert c.eval_count==1 and c.results[0]["status"]=="failed"

def test_journal_truncated_tail_preserved(tmp_path):
    p=tmp_path/"events.jsonl"; p.write_text('{"event":"ok"}\n{"event":')
    assert read_events(p)==[{"event":"ok"}]
    assert p.with_suffix(".truncated").exists()

def test_checkpoint_remains_readable_if_interrupted_before_sidecar_write(tmp_path,monkeypatch):
    from neuroevolution_lab.runtime import save_checkpoint
    save_checkpoint(tmp_path,{"generation":1},0,None)
    original=Path.write_text
    def interrupted(path,*args,**kwargs):
        if path.name=="checkpoint.sha256": raise KeyboardInterrupt()
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,"write_text",interrupted)
    with pytest.raises(KeyboardInterrupt): save_checkpoint(tmp_path,{"generation":2},1,None)
    assert load_checkpoint(tmp_path)["engine"]=={"generation":2}

def test_compressed_evidence_resume_preserves_spent_budget(tmp_path):
    import gzip
    s=spec(budget={"max_evaluations":3})
    assert execute(s,tmp_path)["evaluations"]==3
    path=tmp_path/"events.jsonl"
    path.with_suffix(".jsonl.gz").write_bytes(gzip.compress(path.read_bytes()))
    path.unlink()
    result=resume_run(tmp_path)
    assert result["evaluations"]==3 and result["status"]=="budget_exhausted"

def test_engine_construction_counts_toward_active_wall_budget(tmp_path,monkeypatch):
    import neuroevolution_lab.runtime as runtime
    import neuroevolution_lab.reporting as reporting
    clock=[100.0]
    original=runtime.build_engine
    def construct(s):
        engine=original(s)
        clock[0]+=.25  # Deterministic time spent constructing the actual engine.
        return engine
    monkeypatch.setattr(runtime.time,"monotonic",lambda:clock[0])
    monkeypatch.setattr(runtime,"build_engine",construct)
    monkeypatch.setattr(reporting,"report",lambda path:{"report":"not rendered"})
    result=execute(spec(budget={"wall_seconds":.1}),tmp_path)
    assert result["status"]=="budget_exhausted"
    assert result["evaluations"]==0
    assert result["elapsed_seconds"]==pytest.approx(.25)

@pytest.mark.parametrize("spent_budget",[False,True])
def test_hard_process_exit_preserves_initial_resume_and_journal_clock(tmp_path,spent_budget):
    path=tmp_path/"killed"
    script=textwrap.dedent('''
        import os,sys
        from unittest.mock import patch
        from neuroevolution_lab import runtime
        from neuroevolution_lab.config import ExperimentSpec
        clock=[100.0]
        spent=sys.argv[2]=="True"
        original=runtime.Context.record
        def record(self,event):
            terminal="evaluation_finished" if spent else "evaluation_started"
            if spent and event.get("event")==terminal:
                clock[0]+=3.0
            original(self,event)
            if event.get("event")==terminal:
                os._exit(23)
        spec=ExperimentSpec(method="ga",target="xor",population_size=2,generations=1,
                            budget={"wall_seconds":2 if spent else 600})
        with patch.object(runtime.time,"monotonic",lambda:clock[0]), patch.object(runtime.Context,"record",record):
            runtime.execute(spec,sys.argv[1])
    ''')
    child=subprocess.run([sys.executable,"-c",script,str(path),str(spent_budget)],capture_output=True,text=True,timeout=60)
    assert child.returncode==23,child.stderr
    initial=json.loads((path/"status.json").read_text())
    assert initial["status"]=="running" and initial["evaluations"]==0
    result=resume_run(path)
    if spent_budget:
        # No additional candidate can run even though the old status predates
        # three seconds of durable active work in the first step.
        assert initial["elapsed_seconds"]==0
        assert result["status"]=="budget_exhausted" and result["evaluations"]==1
        assert result["elapsed_seconds"]>=3
    else:
        assert result["status"]=="completed" and result["evaluations"]==2
        clean=execute(ExperimentSpec(method="ga",target="xor",population_size=2,generations=1),tmp_path/"clean")
        assert encoded(result["summary"])==encoded(clean["summary"])

def test_legacy_run_without_status_is_resumable(tmp_path):
    s=spec(model={"provider":"bridge"})
    s.method="llm_workflow"; s.target="arithmetic_tools"
    assert execute(s,tmp_path)["status"]=="waiting_for_model"
    # Historical hard exits could omit status and journals predate clock fields.
    (tmp_path/"status.json").unlink()
    rows=read_events(tmp_path/"events.jsonl")
    for row in rows: row.pop("active_elapsed_seconds",None)
    (tmp_path/"events.jsonl").write_text("".join(encoded(row)+"\n" for row in rows))
    assert resume_run(tmp_path)["status"]=="waiting_for_model"
    assert len(list((tmp_path/"model_requests").glob("*.request.json")))==1

def test_recovered_active_clock_excludes_pause_between_invocations(tmp_path,monkeypatch):
    import neuroevolution_lab.runtime as runtime
    clock=[100.0]
    monkeypatch.setattr(runtime.time,"monotonic",lambda:clock[0])
    ctx=Context(tmp_path,spec())
    clock[0]+=2.0
    ctx.record({"event":"before_pause"})
    clock[0]+=1000.0  # Host bridge work or time before a later resume.
    restored=Context(tmp_path,spec(),elapsed=1.0)
    assert restored.elapsed==2.0
    clock[0]+=1.0
    restored.record({"event":"after_resume"})
    assert restored.rows[-1]["active_elapsed_seconds"]==3.0
