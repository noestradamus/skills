import json
import pytest
from neuroevolution_lab.llm import calculate,validate_genome,AgentEngine,cases
from neuroevolution_lab.config import ExperimentSpec
from neuroevolution_lab.runtime import Context,execute,resume_run
from neuroevolution_lab.providers import next_request,submit_response

def test_arithmetic_is_exact_and_not_eval():
    assert calculate("(3+4)*5-2")==33
    for s in ("__import__('os')","1/0","2**2000","[x for x in range(3)]","("):
        with pytest.raises(ValueError): calculate(s)

def test_typed_workflow_bounds():
    g={"kind":"agent","prompt":"Solve","nodes":["model","calculate"]}
    assert validate_genome(g)==g
    for nodes in (["shell"],["model","shell"],["model"]*7,["model","model"]):
        with pytest.raises(ValueError): validate_genome({**g,"nodes":nodes})

def test_real_bridge_roundtrip_protocol_fixture(tmp_path):
    s=ExperimentSpec(method="llm_workflow",target="arithmetic_tools",population_size=2,generations=1,
                     model={"provider":"bridge"},parameters={"train_cases":2})
    result=execute(s,tmp_path)
    assert result["status"]=="waiting_for_model"
    # Deliberately a deterministic fixture; the acceptance live-model experiment is separate.
    for _ in range(4):
        r=next_request(tmp_path)
        if r["key"].startswith("proposal"):
            response={"kind":"agent","prompt":"Solve","nodes":["model","calculate"]}
        else:
            response={"actions":[{"tool":"calculate","expression":f"({a}+{b})*{c}-{d}"} for a,b,c,d in cases(71,2)]}
        submit_response(tmp_path,r["id"],json.dumps(response),"test fixture; not live model")
        result=resume_run(tmp_path)
    assert result["status"]=="completed"
    assert result["evaluations"]==2 and result["summary"]["best"]["result"]["fitness"]==1

def test_malformed_actions_are_measured_failures(tmp_path,monkeypatch):
    import neuroevolution_lab.llm as llm
    s=ExperimentSpec(method="fixed_agent",target="arithmetic_tools",model={"provider":"bridge"})
    e=AgentEngine(s.model_dump()); ctx=Context(tmp_path,s)
    monkeypatch.setattr(llm,"complete",lambda *a,**k:'{"actions":[]}')
    result=e.evaluate_agent(ctx,e.proposal(ctx,0),0,cases(1,3))
    assert result["fitness"]==0 and not result["constraints"]

def test_neural_router_controls_actual_tool_execution(tmp_path,monkeypatch):
    import neuroevolution_lab.llm as llm
    s=ExperimentSpec(method="neural_router",target="arithmetic_tools",model={"provider":"bridge"})
    e=AgentEngine(s.model_dump()); ctx=Context(tmp_path,s)
    monkeypatch.setattr(llm,"complete",lambda *a,**k:'{"actions":[{"tool":"calculate","expression":"8"}]}')
    g={"kind":"agent","prompt":"Solve","nodes":["model","calculate"],"router":[1,0,0]}
    assert e.evaluate_agent(ctx,g,0,[[1,2,3,1]])["fitness"]==1
    g["router"]=[-1,0,0]
    assert e.evaluate_agent(ctx,g,0,[[1,2,3,1]])["fitness"]==0

def test_crossover_keeps_two_distinct_parents_with_minimum_population(tmp_path,monkeypatch):
    import neuroevolution_lab.llm as llm
    s=ExperimentSpec(method="llm_crossover",target="arithmetic_tools",population_size=2,generations=2,model={"provider":"bridge"})
    e=AgentEngine(s.model_dump()); ctx=Context(tmp_path,s)
    seen=[]
    def model(ctx,messages,key):
        if key.startswith("proposal"):
            request=json.loads(messages[1]["content"]); seen.append(request["parents"])
            return json.dumps({"kind":"agent","prompt":f"candidate {request['candidate']}","nodes":["model","calculate"]})
        return '{"actions":[{"answer":0},{"answer":0}]}'
    monkeypatch.setattr(llm,"complete",model)
    e.step(ctx); e.step(ctx)
    assert all(len(p)==2 and p[0]!=p[1] for p in seen[2:])

def test_archive_reproduction_keeps_best_and_all_alternatives_remain_eligible(monkeypatch):
    observed=set()
    class Ctx:
        def record(self,event): pass
        def evaluate(self,g,fn,**kw): return fn()
    for seed in range(30):
        s=ExperimentSpec(method="llm_workflow",target="arithmetic_tools",seed=seed,population_size=2,model={"provider":"bridge"})
        e=AgentEngine(s.model_dump())
        rows=[{"genome":{"kind":"agent","prompt":str(i),"nodes":["model"]},"result":{"fitness":f,"descriptor":[i/4,0]}} for i,f in enumerate([.1,.2,.3,.9])]
        e.archive={tuple([i,0]):row for i,row in enumerate(rows)}; e.best=rows[-1]
        monkeypatch.setattr(e,"proposal",lambda ctx,i:rows[i]["genome"])
        monkeypatch.setattr(e,"evaluate_agent",lambda ctx,g,i,c:rows[i]["result"])
        e.step(Ctx())
        assert e.population[0]["result"]["fitness"]==.9
        observed.add(e.population[1]["genome"]["prompt"])
    assert observed=={"0","1","2"}

def test_program_replay_preserves_exact_integer_contract(monkeypatch):
    import neuroevolution_lab.llm as llm
    s=ExperimentSpec(method="llm_program",target="arithmetic_tools",model={"provider":"bridge"})
    e=AgentEngine(s.model_dump()); e.best={"genome":{"kind":"program","code":"def solve(a,b,c,d): return float((a+b)*c-d)"}}
    monkeypatch.setattr(llm,"run_program",lambda code,cs,**kw:([float((a+b)*c-d) for a,b,c,d in cs],"fixture"))
    assert e.evaluate_agent(None,e.best["genome"],0,cases(1,3))["fitness"]==0
    assert e.replay(1)["fitness"]==0

def test_heldout_rejects_training_case_overlap(tmp_path):
    from neuroevolution_lab.cli import heldout
    from neuroevolution_lab.runtime import save_checkpoint,rng_state,atomic_json
    s=ExperimentSpec(method="llm_workflow",target="arithmetic_tools",model={"provider":"bridge"})
    e=AgentEngine(s.model_dump()); e.best={"genome":{"kind":"agent","prompt":"Solve","nodes":["model"]}}
    atomic_json(tmp_path/"manifest.json",{"spec":s.model_dump()})
    save_checkpoint(tmp_path,e,0,rng_state())
    with pytest.raises(ValueError,match="overlap"): heldout(tmp_path,tmp_path/"holdout",71,2)

def test_prompt_only_profile_rejects_execution_changing_router(tmp_path,monkeypatch):
    import neuroevolution_lab.llm as llm
    s=ExperimentSpec(method="llm_prompt",target="arithmetic_tools",model={"provider":"bridge"})
    e=AgentEngine(s.model_dump()); ctx=Context(tmp_path,s)
    proposal={"kind":"agent","prompt":"Use the calculator","nodes":["model","calculate"],"router":[-1,0,0]}
    monkeypatch.setattr(llm,"complete",lambda *args,**kwargs:json.dumps(proposal))
    with pytest.raises(ValueError,match="prompts only"):
        e.proposal(ctx,0)
    proposal.pop("router")
    genome=e.proposal(ctx,0)
    assert genome["nodes"]==["model","calculate","verify"] and "router" not in genome

def test_malformed_arithmetic_action_is_scored_without_repair_or_search_abort(tmp_path,monkeypatch):
    import neuroevolution_lab.llm as llm
    s=ExperimentSpec(method="fixed_agent",target="arithmetic_tools",population_size=2,generations=1,
                     model={"provider":"bridge"},parameters={"train_cases":2})
    a,b,c,d=cases(71,2)[1]
    # Protocol fixture: one invalid action and one independently correct action.
    response={"actions":[{"tool":"calculate","expression":"("},{"answer":(a+b)*c-d}]}
    monkeypatch.setattr(llm,"complete",lambda *args,**kwargs:json.dumps(response))
    result=execute(s,tmp_path)
    assert result["status"]=="completed" and result["evaluations"]==2
    best=result["summary"]["best"]["result"]
    assert best["fitness"]==.5
    assert best["metrics"]["outputs"][0]=={"error":"Invalid arithmetic expression syntax","correct":False}
    assert best["metrics"]["outputs"][1]["correct"] is True

@pytest.mark.parametrize("method",["llm_prompt","llm_workflow","fixed_agent","neural_router"])
def test_program_parameter_cannot_change_agent_profile_identity(method):
    s=ExperimentSpec(method=method,target="arithmetic_tools",model={"provider":"bridge"},parameters={"program":True})
    with pytest.raises(ValueError,match="requires llm_program or llm_holdout"):
        AgentEngine(s.model_dump())

def test_program_and_frozen_program_holdout_remain_supported():
    from neuroevolution_lab.llm import HoldoutEngine
    s=ExperimentSpec(method="llm_program",target="arithmetic_tools",model={"provider":"bridge"})
    assert AgentEngine(s.model_dump()).program
    s.method="llm_holdout"
    s.parameters={"program":True,"genome":{"kind":"program","code":"def solve(a,b,c,d): return (a+b)*c-d"}}
    assert HoldoutEngine(s.model_dump()).program
    s.parameters["program"]="false"
    with pytest.raises(ValueError,match="must be a boolean"):
        HoldoutEngine(s.model_dump())

@pytest.mark.parametrize("router",[None,1,True,"abc",{},[1,0],[1,0,float("inf")],[10**400,0,0],[True,0,0]])
def test_invalid_router_fields_raise_clear_validation_errors(router):
    genome={"kind":"agent","prompt":"Solve","nodes":["model","calculate"],"router":router}
    with pytest.raises(ValueError,match="Router requires three finite neural weights"):
        validate_genome(genome)
