"""Run bounded device-operation examples; each backend uses a frozen config.

This is coverage evidence. Five-seed performance measurements have their own
benchmark protocol and are not inferred from these small one-seed examples.
"""
import argparse
from pathlib import Path
from neuroevolution_lab.config import load_spec,Compute
from neuroevolution_lab.compatibility import TORCH_METHODS
from neuroevolution_lab.runtime import execute,replay_run,atomic_json,environment_identity
from neuroevolution_lab.reporting import report
from neuroevolution_lab.devices import resolve_device,device_identity

CASES={"fixed_controller":"fixed-controller-cartpole","random_search":"random-search-cartpole",
       "ga":"ga-xor","es":"es-cartpole","cma_es":"cma-es-xor","nsga2":"nsga2-xor",
       "novelty":"novelty-navigation","nslc":"nslc-navigation","map_elites":"map-elites-navigation",
       "neat":"neat-cartpole","cppn":"cppn-pattern","hyperneat":"hyperneat-navigation",
       "modular_nas":"modular-nas","gradient_refinement":"gradient-refinement",
       "evolutionary_initialization":"evolutionary-initialization","evolved_plasticity":"evolved-plasticity",
       "erl":"erl","differentiable_qd":"differentiable-qd","model_merging":"model-merging",
       "parameter_evolution":"parameter-evolution"}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--devices",nargs="+",default=["cpu","mps"])
    args=parser.parse_args()
    devices=[resolve_device({"device":d}) for d in args.devices]
    root=Path(__file__).resolve().parents[1]
    assert set(CASES)==TORCH_METHODS
    frozen={}
    for method,name in CASES.items():
        s=load_spec(root/"examples"/(name+".toml"))
        s.population_size=8 if method=="differentiable_qd" else 4
        s.generations=2
        s.budget.max_evaluations=32; s.budget.wall_seconds=120
        if s.target in {"cartpole","navigation"}:
            s.parameters["horizon"]=16
            if s.target=="cartpole": s.parameters["episodes"]=2
        if method in {"gradient_refinement","evolutionary_initialization","erl","model_merging","parameter_evolution"}:
            s.learning["inner_steps"]=3
        if method=="erl": s.parameters["horizon"]=8
        if method=="evolved_plasticity": s.parameters["episodes"]=2
        for device in devices:
            key=f"{method}-{str(device).replace(':','-')}"
            candidate=s.model_copy(deep=True)
            candidate.compute=Compute(backend="torch",device=str(device),batch_size=4)
            frozen[key]=candidate
    args.out.mkdir(parents=True,exist_ok=False)
    atomic_json(args.out/"protocol.json",{"scope":"device operation, not comparative superiority",
                "environment":environment_identity(),"devices":[device_identity(d) for d in devices],
                "specs":{key:s.model_dump() for key,s in frozen.items()}})
    records=[]
    for key,s in frozen.items():
        path=args.out/key
        status=execute(s,path)
        row={"key":key,"method":s.method,"device":s.compute.device,"status":status["status"],
             "evaluations":status["evaluations"],"elapsed_seconds":status["elapsed_seconds"],
             "detail":status.get("detail"),"report_error":status.get("report_error")}
        if status["status"]=="completed":
            try:
                row["replay"]=replay_run(path,10000)
                report(path)
            except Exception as exc:
                row["replay_error"]=f"{type(exc).__name__}: {exc}"
        records.append(row)
        atomic_json(args.out/"results.json",records)
        print(key,row["status"],row.get("replay_error",row["detail"]),flush=True)
    failures=[r for r in records if r["status"]!="completed" or r.get("report_error") or r.get("replay_error")]
    atomic_json(args.out/"summary.json",{"profiles":len(CASES),"runs":len(records),"failures":failures})
    if failures: raise SystemExit(1)

if __name__=="__main__": main()
