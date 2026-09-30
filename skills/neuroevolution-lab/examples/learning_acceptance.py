"""Run frozen paired small-CPU protocols; report negative results unchanged.

Example: .venv/bin/python examples/learning_acceptance.py --output runs/learning-acceptance
Never reuse a nonempty output directory. Per-run journals, checkpoints, manifests,
and replay measurements remain under it so selection and costs are inspectable.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import statistics

from neuroevolution_lab.config import load_spec
from neuroevolution_lab.runtime import atomic_json, execute, replay_run


PAIRS = ["gradient-refinement", "evolutionary-initialization", "evolved-plasticity", "erl",
         "differentiable-qd", "model-merging", "parameter-evolution"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2, 3, 4])
    args = parser.parse_args()
    if len(set(args.seeds)) != len(args.seeds):
        parser.error("seeds must be unique")
    args.output.mkdir(parents=True, exist_ok=False)
    examples = Path(__file__).resolve().parent
    frozen = {}
    for family in PAIRS:
        for suffix in ("", "-baseline"):
            path = examples / f"{family}{suffix}.toml"
            frozen[path.name] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                                 "spec": load_spec(path).model_dump()}
    protocol = {"seeds": args.seeds, "examples": frozen,
                "selection": "training/validation only; replay never selects or changes candidates",
                "primary_metric": "replay fitness, except DQD archive coverage",
                "budget_matching": "same candidate evaluation and generation budgets within each pair; report inner costs separately",
                "caveat": "five seeds on small synthetic tasks support bounded observations, not general superiority"}
    atomic_json(args.output / "protocol.json", protocol)
    records, comparisons = [], []
    for family in PAIRS:
        paired = []
        for seed in args.seeds:
            outcomes = {}
            for condition, suffix in (("method", ""), ("control", "-baseline")):
                model = load_spec(examples / f"{family}{suffix}.toml").model_copy(update={"seed": seed})
                path = args.output / family / f"seed-{seed}-{condition}"
                run = execute(model, path)
                if run["status"] != "completed":
                    raise RuntimeError(f"{path}: {run['status']}: {run['detail']}")
                replay = replay_run(path, seed=10000+seed)
                primary = run["summary"]["coverage"] if family == "differentiable-qd" else replay["fitness"]
                record = {"family": family, "condition": condition, "seed": seed, "primary": primary,
                          "evaluations": run["evaluations"], "elapsed_seconds": run["elapsed_seconds"],
                          "summary": run["summary"], "replay": replay, "run_path": str(path.relative_to(args.output))}
                outcomes[condition] = record
                records.append(record)
            delta = outcomes["method"]["primary"]-outcomes["control"]["primary"]
            paired.append(delta)
            atomic_json(args.output / "results.json", records)
        comparisons.append({"family": family, "metric": "coverage" if family == "differentiable-qd" else "replay_fitness",
                            "paired_differences_method_minus_control": paired,
                            "mean_difference": statistics.mean(paired),
                            "std_difference": statistics.stdev(paired) if len(paired) > 1 else 0.,
                            "wins_ties_losses": [sum(d > 0 for d in paired), sum(d == 0 for d in paired), sum(d < 0 for d in paired)],
                            "conclusion": "descriptive only; no significance or general-superiority claim"})
        atomic_json(args.output / "summary.json", {"protocol": "protocol.json", "comparisons": comparisons,
                                                   "completed_runs": len(records)})
    print(json.dumps({"output": str(args.output), "completed_runs": len(records), "comparisons": comparisons}, indent=2))


if __name__ == "__main__":
    main()
