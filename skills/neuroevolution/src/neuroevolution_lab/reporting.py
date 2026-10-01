"""Self-contained measured reports and static figures, with no live dashboard."""
import json
import gzip
from pathlib import Path
from .runtime import read_events, plain, atomic_json,load_checkpoint

def report(path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    path=Path(path).resolve()
    manifest=json.loads((path/"manifest.json").read_text())
    status=json.loads((path/"status.json").read_text())
    rows=read_events(path/"events.jsonl")
    if not rows and (path/"events.jsonl.gz").exists():
        rows=[json.loads(line) for line in gzip.decompress((path/"events.jsonl.gz").read_bytes()).decode().splitlines()]
    finished=[r for r in rows if r.get("event")=="evaluation_finished"]
    measured=[r for r in finished if r.get("status")=="ok" and r["result"].get("measurement_kind")=="observed"]
    predicted=[r for r in finished if r.get("status")=="ok" and r["result"].get("measurement_kind")=="predicted"]
    failures=[r for r in finished if r.get("status")=="failed"]
    spec=manifest["spec"]; summary=status.get("summary",{})
    images=[]
    if summary.get("best_genome") and (spec["method"] in {"neat","cppn","hyperneat","modular_nas"} or isinstance(summary["best_genome"],dict) and summary["best_genome"].get("encoding")=="direct_mlp"):
        from .structural import render_genome
        render_genome(summary,path/"network.svg")
        images.append(("Actual saved neural genes and expressed connections","network.svg"))
    if spec["method"]=="map_elites":
        engine=load_checkpoint(path)["engine"]
        data=engine.qd_archive.data()
        atomic_json(path/"archive.json",plain(data))
        if len(data["objective"]):
            fig,ax=plt.subplots(figsize=(5,4),layout="constrained")
            im=ax.scatter(data["measures"][:,0],data["measures"][:,1],c=data["objective"],marker="s",s=80)
            ax.set(title="Retained archive occupants",xlabel="Descriptor 1",ylabel="Descriptor 2")
            fig.colorbar(im,ax=ax,label="Measured fitness"); fig.savefig(path/"archive.svg"); plt.close(fig)
            images.append(("Actual retained MAP-Elites archive","archive.svg"))
    if measured:
        fig,ax=plt.subplots(figsize=(7,3.6),layout="constrained")
        x=[r["id"] for r in measured]; y=[r["result"]["fitness"] for r in measured]
        ax.scatter(x,y,s=12,alpha=.45,label="Observed fitness")
        running=[]; best=float("-inf")
        for v in y: best=max(best,v); running.append(best)
        ax.plot(x,running,label="Best observed")
        if predicted: ax.scatter([r["id"] for r in predicted],[r["result"]["fitness"] for r in predicted],marker="x",label="Surrogate prediction")
        ax.set(xlabel="Dispatched evaluation ID",ylabel="Fitness (maximize)",title=spec["name"])
        ax.legend(); fig.savefig(path/"learning-curve.svg"); plt.close(fig)
        images.append(("Observed evaluations and best-so-far curve","learning-curve.svg"))
        descriptors=[r["result"]["descriptor"] for r in measured]
        if all(len(d)==2 for d in descriptors):
            fig,ax=plt.subplots(figsize=(5,4),layout="constrained")
            artist=ax.scatter([d[0] for d in descriptors],[d[1] for d in descriptors],c=y,s=18,cmap="viridis")
            ax.set(xlabel="Descriptor 1",ylabel="Descriptor 2",title="Observed behavioral space")
            fig.colorbar(artist,ax=ax,label="Fitness"); fig.savefig(path/"behavior-space.svg"); plt.close(fig)
            images.append(("Measured behaviors (archive membership is in summary.json)","behavior-space.svg"))
        trajectories=[r["result"].get("metrics",{}).get("trajectory") for r in measured]
        trajectories=[t for t in trajectories if t and isinstance(t[0],list) and len(t[0])==2]
        if trajectories:
            fig,ax=plt.subplots(figsize=(5,4),layout="constrained")
            for t in trajectories[-20:]: ax.plot([p[0] for p in t],[p[1] for p in t],alpha=.4)
            ax.plot([.5,.5],[0,.8],color="black",linewidth=3); ax.scatter([.9],[.5],marker="*",s=100)
            ax.set(xlim=(0,1),ylim=(0,1),xlabel="x",ylabel="y",title="Last 20 measured navigation trajectories")
            fig.savefig(path/"trajectories.svg"); plt.close(fig); images.append(("Navigation trajectories","trajectories.svg"))
    responses=[json.loads(p.read_text()) for p in (path/"model_requests").glob("*.response.json")]
    usage={"requests":len(list((path/"model_requests").glob("*.request.json"))),"responses":len(responses),
           "endpoint_cost_usd":sum(r.get("cost_usd",0) for r in responses),
           "observable_tokens":sum((r.get("usage") or {}).get("total_tokens",0) for r in responses),
           "unobserved_usage_responses":sum(r.get("usage") is None for r in responses)}
    resources={"dispatches":status["evaluations"],"observed":len(measured),"predicted":len(predicted),"failed":len(failures),
               "unfinished":status["evaluations"]-len(finished),"active_wall_seconds":status["elapsed_seconds"],"model":usage}
    resources["compute"]=spec.get("compute",{"device":"cpu","backend":"reference"})
    resources["device_memory"]=status.get("device_memory",{})
    resources["batches"]=[r for r in rows if r.get("event")=="batch_finished"]
    resources["method_counters"]={k:v for k,v in summary.items() if any(word in k for word in ("steps","updates","interactions","queries","transfers","training"))}
    lineage=[r for r in rows if "parents" in r or "ancestry" in r or r.get("event") in {"variation","inheritance","poet_transfer"}]
    atomic_json(path/"lineage.json",lineage)
    # Keep complete raw metrics: episodes/interactions/gradient updates differ by domain.
    atomic_json(path/"summary.json",summary); atomic_json(path/"resources.json",resources)
    best=summary.get("best_genome",summary.get("best",summary.get("best_controller")))
    if best is not None: atomic_json(path/"candidate.json",best)
    replay_files=sorted(path.glob("replay-*.json"))
    lines=[f"# {spec['name']}","",f"Method `{spec['method']}` on `{spec['target']}`. Status: **{status['status']}**.","",
           "This report describes the configured bounded experiment. It does not establish general algorithm superiority or large-model effectiveness.","",
           "## Measured evidence","",f"{len(measured)} observed evaluations, {len(predicted)} surrogate predictions, {len(failures)} failures, {resources['unfinished']} unfinished dispatches.",
           f"Active execution time: {status['elapsed_seconds']:.3f} seconds. One orchestration process; numerical compute: `{resources['compute']}`. Model requests: {usage['requests']}.","",
           "Model usage may be unobservable for host-agent responses. Zero additional endpoint cost does not mean zero inference cost.","",
           "Comparisons and uncertainty require the frozen multi-seed protocol; this single run is not an uncertainty estimate.",""]
    for title,file in images: lines.extend([f"![{title}]({file})",""])
    lines.extend(["## State and replay","",f"Configured population: {spec['population_size']}; generations: {spec['generations']}. Recorded lineage/transfer/inheritance events: {len(lineage)}.","","Full candidates, ancestry, archives, species and learning state are preserved in the local checkpoint and event journal. [Summary](summary.json), [resources](resources.json), [events](events.jsonl), [lineage](lineage.json).", "",
                  "Checkpoints use pickle and must only be loaded from trusted local runs.","",f"Replay command (from the installed skill environment): `neuroevo replay '{path}' --seed 10000`.","",
                  "Executed replays: "+(", ".join(f"[{p.name}]({p.name})" for p in replay_files) or "none yet"),"",
                  "## Configuration and environment","","```json",json.dumps(manifest,indent=2),"```","",
                  "## Failures","",json.dumps(failures,indent=2) if failures else "No evaluator failures recorded.","",
                  "## Sources and adaptations","","Consult the packaged `references/book-to-capability.md` for defining mechanisms and primary sources, and the relevant method reference for this profile's departures. The manifest identifies exact source and dependency hashes.",""])
    groups={"structural":{"neat","cppn","hyperneat","modular_nas"},
            "learning":{"gradient_refinement","evolutionary_initialization","evolved_plasticity","erl","differentiable_qd","model_merging","parameter_evolution"},
            "ecology":{"cooperative","competitive","poet","surrogate"},
            "llm":{"llm_prompt","llm_workflow","llm_program","llm_mutation","llm_crossover","neural_router","fixed_agent","random_agent","greedy_agent","llm_holdout"}}
    reference=next((group for group,methods in groups.items() if spec["method"] in methods),"search")
    source=Path(__file__).resolve().parents[2]/"references"/(reference+".md")
    if source.exists():
        lines.extend(["## Method specification and adaptations","",source.read_text(),""])
    (path/"report.md").write_text("\n".join(lines))
    return {"report":str(path/"report.md"),"resources":resources}
