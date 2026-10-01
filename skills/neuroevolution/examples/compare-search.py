"""Freeze and execute a bounded five-seed controller comparison.

Usage: python examples/compare-search.py /absolute/new/output-directory
The output directory must not exist. Reports are measured evidence, not a claim
that the small protocol establishes which algorithm is generally superior.
"""
import json
import argparse
from pathlib import Path

import numpy as np

from neuroevolution_lab.config import ExperimentSpec
from neuroevolution_lab.runtime import execute, load_checkpoint, atomic_json


PROTOCOL = {
    "methods": ["random_search", "ga", "es", "cma_es"], "seeds": [0, 1, 2, 3, 4],
    "target": "cartpole", "population_size": 12, "generations": 8,
    "parameters": {"hidden": 4, "horizon": 80, "episodes": 3, "sigma": .3, "learning_rate": .03},
    "budget": {"max_evaluations": 96, "wall_seconds": 180},
    "heldout_seeds": [10000, 10100, 10200, 10300, 10400],
    "selection": "best_training_fitness",
    "reporting": "all seeds, raw per-seed train/heldout values, medians, no selective exclusions",
    "claim_scope": "bounded local reference task; no general algorithm superiority inference",
}

NAVIGATION_PROTOCOL = {
    "methods": ["ga", "novelty", "nslc", "map_elites"], "seeds": [0, 1, 2, 3, 4],
    "target": "navigation", "population_size": 16, "generations": 12,
    "parameters": {"hidden": 4, "horizon": 100, "sigma": .3, "neighbors": 5,
                   "novelty_threshold": .05, "bins": 8, "archive_parent_probability": .25},
    "budget": {"max_evaluations": 192, "wall_seconds": 180},
    "heldout_seeds": [10000, 10100, 10200, 10300, 10400],
    "selection": "best_training_fitness_for_common_task_measure; full_archive_retained_for_diversity",
    "reporting": "all seeds, objective-only GA comparison, measured coverage for QD, no selective exclusions",
    "claim_scope": "bounded deceptive navigation; novelty/QD need not beat objective search under every seed",
}

FIXED_PROTOCOL = {
    **PROTOCOL, "methods": ["fixed_controller"], "population_size": 2, "generations": 1,
    "budget": {"max_evaluations": 1, "wall_seconds": 120},
    "selection": "one seeded initial controller, no optimization and no best-of-samples",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    choice = parser.add_mutually_exclusive_group()
    choice.add_argument("--navigation", action="store_true")
    choice.add_argument("--fixed", action="store_true")
    args = parser.parse_args()
    protocol = NAVIGATION_PROTOCOL if args.navigation else FIXED_PROTOCOL if args.fixed else PROTOCOL
    root = Path(args.output).resolve()
    root.mkdir(parents=True, exist_ok=False)
    atomic_json(root / "protocol.json", protocol)
    rows = []
    for method in protocol["methods"]:
        for seed in protocol["seeds"]:
            run = root / f"{method}-{seed}"
            spec = ExperimentSpec(method=method, target=protocol["target"], seed=seed,
                                  population_size=protocol["population_size"], generations=protocol["generations"],
                                  parameters=protocol["parameters"], budget=protocol["budget"])
            result = execute(spec, run)
            row = {"method": method, "seed": seed, "status": result["status"],
                   "evaluations": result["evaluations"], "seconds": result["elapsed_seconds"],
                   "training_fitness": result["summary"]["best_fitness"]}
            if result["status"] == "completed":
                engine = load_checkpoint(run)["engine"]
                row["heldout_results"] = [engine.replay(seed=s) for s in protocol["heldout_seeds"]]
                row["heldout_mean"] = float(np.mean([r["fitness"] for r in row["heldout_results"]]))
                if "coverage" in result["summary"]:
                    row["archive_coverage"] = result["summary"]["coverage"]
                    row["qd_score"] = result["summary"]["qd_score"]
                if args.navigation:
                    row["heldout_success_rate"] = float(np.mean([r["metrics"]["success"] for r in row["heldout_results"]]))
            rows.append(row)
            atomic_json(root / "measurements.json", rows)
            print(json.dumps({k: v for k, v in row.items() if k != "heldout_results"}), flush=True)
    aggregates = {}
    for method in protocol["methods"]:
        observed = [r for r in rows if r["method"] == method and r["status"] == "completed"]
        aggregates[method] = {"completed_seeds": len(observed),
                              "training_median": float(np.median([r["training_fitness"] for r in observed])) if observed else None,
                              "heldout_median": float(np.median([r["heldout_mean"] for r in observed])) if observed else None}
    atomic_json(root / "aggregate.json", aggregates)


if __name__ == "__main__":
    main()
