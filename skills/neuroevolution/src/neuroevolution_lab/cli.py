"""Public experiment CLI. JSON output is also suitable for an operating agent."""
import argparse
import importlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from .config import ExperimentSpec,load_spec
from .runtime import execute,resume_run,replay_run,load_checkpoint,environment_identity,encoded,registry
from .compatibility import validate_compatibility
from .providers import next_request,submit_response
from .sandbox import DEFAULT_IMAGE

def doctor():
    from .devices import capabilities
    from .compatibility import TORCH_METHODS
    checks={}
    for name in ("numpy","scipy","neat","cma","ribs","pymoo","torch","gymnasium","httpx"):
        try: importlib.import_module(name); checks[name]="imported"
        except Exception as e: checks[name]=str(e)
    docker={"client":bool(shutil.which("docker")),"server":False}
    if docker["client"]:
        try:
            result=subprocess.run(["docker","info","--format","{{.OSType}}/{{.Architecture}}"],capture_output=True,text=True,timeout=15)
            docker.update(server=result.returncode==0,identity=result.stdout.strip())
        except subprocess.TimeoutExpired: docker["detail"]="daemon check timed out"
    return {"environment":environment_identity(),"imports":checks,"docker":docker,"methods":sorted(registry()),
            "devices":capabilities(),"torch_methods":sorted(TORCH_METHODS),
            "ready":all(v=="imported" for v in checks.values()) and sys.version_info[:2]==(3,12),
            "note":"Import success is a dependency check, not algorithm validation. Program execution additionally requires a local Docker image."}

def heldout(path,out,seed=10000,count=8):
    path=Path(path); manifest=json.loads((path/"manifest.json").read_text())
    engine=load_checkpoint(path)["engine"]
    if not getattr(engine,"best",None) or not isinstance(engine.best,dict) or "genome" not in engine.best:
        raise ValueError("evaluate-heldout is for saved LLM-agent genomes; use replay for neural profiles")
    from .llm import cases
    if count<1: raise ValueError("Heldout case count must be positive")
    if {tuple(c) for c in cases(seed,count)} & {tuple(c) for c in engine.training}:
        raise ValueError("Requested heldout cases overlap training cases; choose a different seed")
    spec=ExperimentSpec.model_validate(manifest["spec"])
    spec.method="llm_holdout"; spec.name+="-heldout"; spec.seed=seed; spec.generations=1
    spec.parameters={"genome":engine.best["genome"],"cases":count,"program":engine.program,
                     "docker_image":spec.parameters.get("docker_image",DEFAULT_IMAGE),"training_run":str(path.resolve())}
    return execute(spec,out)

def main(argv=None):
    parser=argparse.ArgumentParser(prog="neuroevo")
    sub=parser.add_subparsers(dest="command",required=True)
    sub.add_parser("doctor")
    for command in ("validate","run"):
        p=sub.add_parser(command); p.add_argument("spec")
        if command=="run": p.add_argument("--out",required=True)
    for command in ("resume","inspect","report","replay","evaluate-heldout"):
        p=sub.add_parser(command); p.add_argument("run")
        if command in ("replay","evaluate-heldout"): p.add_argument("--seed",type=int,default=10000)
        if command=="evaluate-heldout": p.add_argument("--out",required=True); p.add_argument("--cases",type=int,default=8)
    p=sub.add_parser("bridge"); bs=p.add_subparsers(dest="bridge_command",required=True)
    n=bs.add_parser("next"); n.add_argument("run")
    s=bs.add_parser("submit"); s.add_argument("run"); s.add_argument("request_id"); s.add_argument("--response",required=True); s.add_argument("--provenance",required=True)
    args=parser.parse_args(argv)
    try:
        if args.command=="doctor": value=doctor()
        elif args.command in ("validate","run"):
            spec=load_spec(args.spec)
            if args.command=="validate":
                value=validate_compatibility(spec)
                from .runtime import build_engine
                build_engine(spec)
            else: value=execute(spec,args.out)
        elif args.command=="resume": value=resume_run(args.run)
        elif args.command=="inspect": value=json.loads((Path(args.run)/"status.json").read_text())
        elif args.command=="report":
            from .reporting import report
            value=report(args.run)
        elif args.command=="replay": value=replay_run(args.run,args.seed)
        elif args.command=="evaluate-heldout": value=heldout(args.run,args.out,args.seed,args.cases)
        elif args.bridge_command=="next": value=next_request(args.run)
        else:
            submit_response(args.run,args.request_id,Path(args.response).read_text(),args.provenance); value={"submitted":args.request_id}
        print(encoded(value))
        return 1 if isinstance(value,dict) and (value.get("status")=="failed" or value.get("ready") is False) else 0
    except (ValueError,OSError,KeyError) as e:
        print(encoded({"error":str(e)}),file=sys.stderr); return 2

if __name__=="__main__": raise SystemExit(main())
