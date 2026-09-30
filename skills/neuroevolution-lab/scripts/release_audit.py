"""Audit a local evidence directory; never substitutes imports for execution.

Usage: .venv/bin/python scripts/release_audit.py --evidence /path/to/local/runs
Writes coverage and current package source hashes into that directory.
Generated evidence is not distributed with the skill.
"""
import argparse
import hashlib
import json
from pathlib import Path
from neuroevolution_lab.runtime import registry,environment_identity,atomic_json

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence",type=Path,required=True,help="Existing local directory containing saved runs")
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]; evidence=args.evidence.resolve()
    if not evidence.is_dir():
        parser.error(f"Evidence directory does not exist: {evidence}")
    methods={name:{"executed_runs":[],"partial_runs":[]} for name in sorted(registry())}
    problems=[]
    for p in sorted(evidence.rglob("status.json")):
        state=json.loads(p.read_text()); name=state.get("method")
        if name not in methods: continue
        row={"path":str(p.parent.relative_to(evidence)),"evaluations":state["evaluations"],"status":state["status"],
             "compute":state.get("compute",{"backend":"reference","device":"cpu"})}
        if name in {"neat","cppn","hyperneat"}:
            row["evolution_profile"]=state.get("summary",{}).get("evolution_profile","legacy")
        methods[name]["executed_runs" if state["status"]=="completed" else "partial_runs"].append(row)
        if state.get("report_error"): problems.append({"path":row["path"],"report_error":state["report_error"]})
        if state["status"] in {"completed","budget_exhausted"} and not (p.parent/"report.md").exists():
            problems.append({"path":row["path"],"missing":"report.md"})
    missing=[m for m,d in methods.items() if not d["executed_runs"]]
    result={"environment":environment_identity(),"methods":methods,"missing_executed_profiles":missing,"artifact_problems":problems,
            "scope":"This audit inventories saved runs and missing reports. It does not verify algorithm correctness, artifact provenance, skill usability, accelerator support, or comparative performance."}
    atomic_json(evidence/"coverage.json",result)
    sources={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ("src","tests","references","examples","scripts","agents") for p in (root/folder).rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    for name in ("SKILL.md","README.md","pyproject.toml","uv.lock","Dockerfile",".python-version",".gitignore",".dockerignore",
                 "environments/cuda/pyproject.toml","environments/cuda/uv.lock"):
        sources[name]=hashlib.sha256((root/name).read_bytes()).hexdigest()
    atomic_json(evidence/"release-source-hashes.json",sources)
    print(json.dumps({"profiles":len(methods),"missing":missing,"problems":problems}))
    if missing or problems: raise SystemExit(1)

if __name__=="__main__": main()
