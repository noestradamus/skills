"""Frozen five-seed kernel comparison; no claim about entire-search throughput."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import statistics
import time
import numpy as np
import torch
from neuroevolution_lab.accelerator_learning import refine_sine_population
from neuroevolution_lab.learning import make_mlp,vector,refine_sine
from neuroevolution_lab.devices import resolve_device,synchronize,memory_stats,device_identity
from neuroevolution_lab.runtime import atomic_json,environment_identity


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--devices",nargs="+",default=["cpu","mps"])
    p.add_argument("--seeds",type=int,nargs="+",default=[0,1,2,3,4])
    p.add_argument("--population",type=int,default=256)
    p.add_argument("--hidden",type=int,default=128)
    p.add_argument("--steps",type=int,default=24)
    args=p.parse_args()
    if len(set(args.seeds))!=len(args.seeds) or not args.seeds: p.error("Provide distinct seeds")
    if min(args.population,args.hidden,args.steps)<1: p.error("Work sizes must be positive")
    devices=[resolve_device({"device":d}) for d in args.devices]
    torch.set_num_threads(1)
    args.out.mkdir(parents=True,exist_ok=False)
    protocol={"seeds":args.seeds,"population":args.population,"hidden":args.hidden,"steps":args.steps,
              "task":[1.2,.1],"learning_rate":.03,"support_samples":24,"query_samples":48,
              "devices":[device_identity(d) for d in devices],"environment":environment_identity(),
              "warmup":"one scalar CPU and one 4-candidate batched call per device, each with 2 steps, before timing",
              "timing":"synchronized wall time including batch transfers and returned measurements; excludes search selection/journal/report",
              "comparison":"scalar CPU independent SGD; batched torch CPU and actual selected accelerator",
              "agreement":{"weights_rtol":2e-4,"weights_atol":2e-5,"fitness_rtol":2e-4,"fitness_atol":2e-5}}
    atomic_json(args.out/"protocol.json",protocol)
    warm=np.stack([vector(make_mlp(1,args.hidden,1,i)) for i in range(4)])
    refine_sine(warm[0],args.hidden,(1.2,.1),100,101,2,.03)
    for device in devices:
        refine_sine_population(warm,args.hidden,(1.2,.1),100,101,2,.03,device)
        synchronize(device)
    records=[]
    for seed in args.seeds:
        weights=np.stack([vector(make_mlp(1,args.hidden,1,seed*100000+i)) for i in range(args.population)])
        support,query=10000+seed*2,10001+seed*2
        start=time.perf_counter()
        scalar=[refine_sine(w,args.hidden,(1.2,.1),support,query,args.steps,.03) for w in weights]
        scalar_seconds=time.perf_counter()-start
        reference=np.stack([s[0] for s in scalar]); losses=np.array([s[1]["query_mse"] for s in scalar])
        row={"seed":seed,"backend":"reference","device":"cpu","seconds":scalar_seconds,
             "candidate_gradient_steps":args.population*args.steps,"mean_query_mse":float(losses.mean())}
        records.append(row)
        for device in devices:
            synchronize(device)
            start=time.perf_counter()
            actual,metrics=refine_sine_population(weights,args.hidden,(1.2,.1),support,query,args.steps,.03,device)
            synchronize(device)
            seconds=time.perf_counter()-start
            actual_losses=np.array([m["query_mse"] for m in metrics])
            agrees=bool(np.allclose(actual,reference,rtol=2e-4,atol=2e-5) and np.allclose(actual_losses,losses,rtol=2e-4,atol=2e-5))
            records.append({"seed":seed,"backend":"torch","device":str(device),"seconds":seconds,
                            "candidate_gradient_steps":args.population*args.steps,"scalar_cpu_speed_ratio":scalar_seconds/seconds,
                            "max_weight_difference":float(np.max(np.abs(actual-reference))),
                            "max_query_mse_difference":float(np.max(np.abs(actual_losses-losses))),
                            "mean_query_mse":float(actual_losses.mean()),"agreement_passed":agrees,
                            "memory":memory_stats(device)})
            atomic_json(args.out/f"losses-seed-{seed}-{str(device).replace(':','-')}.json",
                        {"reference":losses.tolist(),"batched":actual_losses.tolist()})
            atomic_json(args.out/"measurements.json",records)
            if not agrees: raise RuntimeError(f"Numerical agreement failed: seed={seed},device={device}; evidence retained")
        print(json.dumps({"seed":seed,"completed":True}),flush=True)
    groups={}
    for row in records: groups.setdefault(f"{row['backend']}/{row['device']}",[]).append(row["seconds"])
    medians={key:statistics.median(values) for key,values in groups.items()}
    summary={"timing_scope":protocol["timing"],"median_seconds":medians,
             "cpu_reference_over_backend":{key:medians["reference/cpu"]/value for key,value in medians.items()},
             "torch_cpu_over_backend":{key:medians.get("torch/cpu",float("nan"))/value for key,value in medians.items()} if "torch/cpu" in medians else {},
             "all_agreement_passed":all(row.get("agreement_passed",True) for row in records),
             "claim_boundary":"One dense inner-learning workload; not all methods, entire experiments or discovery quality."}
    atomic_json(args.out/"summary.json",summary)
    lines=["# Accelerator kernel comparison","",summary["claim_boundary"],"",protocol["timing"],"",
           "| Backend/device | Median seconds | CPU scalar / backend |","| --- | ---: | ---: |"]
    for key,value in medians.items(): lines.append(f"| {key} | {value:.6f} | {medians['reference/cpu']/value:.3f} |")
    lines += ["","Ratios greater than one indicate lower elapsed time than scalar CPU. Compare torch CPU with the accelerator separately to distinguish batching gains from hardware gains.","",
              "[Frozen protocol](protocol.json), [all measurements](measurements.json), [summary](summary.json)."]
    (args.out/"REPORT.md").write_text("\n".join(lines)+"\n")
    print(json.dumps(summary,indent=2))


if __name__=="__main__": main()
