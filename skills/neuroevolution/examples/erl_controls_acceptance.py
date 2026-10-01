"""Frozen equal-interaction comparison of hybrid ERL, pure evolution and DDPG."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics

from neuroevolution_lab.config import load_spec
from neuroevolution_lab.runtime import atomic_json, execute, replay_run


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    examples = Path(__file__).resolve().parent
    names = {"hybrid": "erl.toml", "evolution_only": "erl-evolution-only.toml", "learning_only": "erl-learning-only.toml"}
    files = {condition: {"spec": load_spec(examples/name).model_dump(),
                        "sha256": hashlib.sha256((examples/name).read_bytes()).hexdigest()}
             for condition, name in names.items()}
    sources = {name: hashlib.sha256((examples.parent/"src"/"neuroevolution_lab"/name).read_bytes()).hexdigest()
               for name in ["learning.py", "models.py"]}
    atomic_json(args.output/"protocol.json", {"seeds": [0, 1, 2, 3, 4], "conditions": files, "source_sha256": sources,
                "interaction_budget": "Each condition uses 15 training rollouts of 20 steps = 300 interactions",
                "gradient_cost": "Hybrid and DDPG: 15 actor plus 15 critic updates; evolution: zero",
                "selection": "Hybrid/evolution select observed population policy; DDPG returns final actor",
                "metric": "mean reward on 8 fresh evaluation rollouts; never used for training or selection"})
    rows = []
    for seed in range(5):
        for condition, filename in names.items():
            spec = load_spec(examples/filename).model_copy(update={"seed": seed})
            path = args.output/f"seed-{seed}-{condition}"
            run = execute(spec, path)
            if run["status"] != "completed":
                raise RuntimeError(run)
            replay = replay_run(path, seed=10000+seed)
            rows.append({"seed": seed, "condition": condition, "status": run, "replay": replay})
            atomic_json(args.output/"results.json", rows)
    comparisons = []
    for control in ["evolution_only", "learning_only"]:
        differences = []
        for seed in range(5):
            pair = {r["condition"]:r["replay"]["fitness"] for r in rows if r["seed"] == seed}
            differences.append(pair["hybrid"]-pair[control])
        comparisons.append({"comparison": f"hybrid_minus_{control}", "paired_differences": differences,
                            "mean_difference": statistics.mean(differences),
                            "wins_ties_losses": [sum(d>0 for d in differences),sum(d==0 for d in differences),sum(d<0 for d in differences)],
                            "interpretation": "bounded descriptive comparison; no general superiority claim"})
    summary = {"completed_runs": len(rows), "comparisons": comparisons,
               "all_training_interactions_equal": all(r["status"]["summary"]["environment_interactions"] == 300 for r in rows)}
    atomic_json(args.output/"summary.json", summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
