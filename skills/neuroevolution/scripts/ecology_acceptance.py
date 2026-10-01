"""Freeze and run bounded ecology acceptance. Execute with the package's Python.

Usage: .venv/bin/python scripts/ecology_acceptance.py --output PATH
PATH must not exist. All specifications and relevant sources are hashed before
the first search starts. Every raw run is retained with a compressed journal;
selected seed-zero full-method runs also have the historical convenience paths.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import tomllib


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n")


def freeze_source(package, frozen):
    """Keep the full import closure as modules evolve; never use a fixed subset."""
    frozen.mkdir(parents=True)
    for source in sorted((package / "src" / "neuroevolution_lab").glob("*.py")):
        shutil.copy2(source, frozen / source.name)


def retain_run(source, destination):
    """Retain every candidate/checkpoint, with lossless journal compression."""
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns("events.jsonl"))
    with gzip.open(destination / "events.jsonl.gz", "wb") as stream:
        stream.write((source / "events.jsonl").read_bytes())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    package = Path(__file__).resolve().parents[1]
    frozen = output / "frozen_source" / "neuroevolution_lab"
    freeze_source(package, frozen)
    shutil.copy2(__file__, output / "protocol.py")
    sys.path.insert(0, str(frozen.parent))
    import numpy as np
    from neuroevolution_lab.config import ExperimentSpec
    from neuroevolution_lab.ecology import (
        competitive_panel, fixed_opponents, network_size, prescription_episode, terrain_episode,
    )
    from neuroevolution_lab.runtime import execute, load_checkpoint, replay_run

    names = ["cooperative", "cooperative-baseline", "competitive", "competitive-baseline",
             "poet", "poet-baseline", "poet-direct-baseline", "surrogate", "surrogate-baseline"]
    (output / "specs").mkdir()
    specifications = []
    for name in names:
        original = tomllib.loads((package / "examples" / f"{name}.toml").read_text())
        for seed in range(5):
            data = {**original, "seed": seed, "generations": 1000,
                    "budget": {**original["budget"], "max_evaluations": 500, "wall_seconds": 180}}
            spec = ExperimentSpec.model_validate(data)
            key = f"{name}-seed-{seed}"
            path = output / "specs" / f"{key}.json"
            write_json(path, spec.model_dump())
            specifications.append((name, key, spec))
    raw_root = Path(tempfile.mkdtemp(prefix="neuroevolution-ecology-frozen-"))
    heldout_seeds = list(range(10000, 10005))
    heldout_opponents = np.vstack([fixed_opponents()[:3],
        np.random.default_rng(987311).normal(0, 0.9, (9, network_size(6, outputs=3)))])
    common_environments = np.array([[0.35, 0.7, 0.0, 0.1], [0.6, 1.2, 0.15, 0.15],
                                   [0.8, 1.7, -0.2, 0.25], [0.5, 1.9, 0.25, 0.07]])
    write_json(output / "heldout-opponents.json", heldout_opponents.tolist())
    write_json(output / "heldout-environments.json", common_environments.tolist())
    manifest = {"protocol": "bounded-ecology-five-seed-v2", "search_seeds": list(range(5)),
                "heldout_rollout_seeds": heldout_seeds, "raw_run_storage": str(raw_root),
                "source_sha256": {p.name: digest(p) for p in sorted(frozen.glob("*.py"))},
                "spec_sha256": {p.name: digest(p) for p in sorted((output / "specs").glob("*.json"))},
                "protocol_sha256": digest(output / "protocol.py"),
                "heldout_opponents_sha256": digest(output / "heldout-opponents.json"),
                "heldout_environments_sha256": digest(output / "heldout-environments.json"),
                "frozen_before_execution": True,
                "comparison_limit": "Equal journal caps, variable whole-generation use; report actual games/true queries. No superiority claim."}
    write_json(output / "frozen-manifest.json", manifest)
    print(json.dumps({"frozen_manifest": str(output / "frozen-manifest.json"), "sha256": digest(output / "frozen-manifest.json")}), flush=True)

    records = []
    for name, key, spec in specifications:
        path = raw_root / key
        result = execute(spec, path)
        if result["status"] not in ("completed", "budget_exhausted"):
            raise RuntimeError(f"{key}: {result['status']}: {result.get('detail')}")
        cp = load_checkpoint(path)
        engine = cp["engine"]
        if not engine.generation:
            raise RuntimeError(f"{key}: no complete generation")
        same_seed = replay_run(path, seed=spec.seed)
        if abs(same_seed["fitness"] - engine.best_fitness) > 1e-12:
            raise RuntimeError(f"{key}: saved-best replay mismatch")
        replay_scores = [float(engine.replay(seed=seed)["fitness"]) for seed in heldout_seeds]
        row = {"condition": name, "search_seed": spec.seed, "run_path": str(path),
               "spec_sha256": manifest["spec_sha256"][f"{key}.json"],
               "checkpoint_sha256": digest(path / "checkpoint.pkl"), "status": result["status"],
               "evaluations_started": result["evaluations"], "committed_evaluations": cp["cursor"],
               "partial_generation_evaluations": result["evaluations"] - cp["cursor"],
               "generation": engine.generation, "saved_fitness": engine.best_fitness,
               "retained_run": f"runs/{key}",
               "same_seed_replay_fitness": same_seed["fitness"], "replay_seed_scores": replay_scores,
               "replay_mean": float(np.mean(replay_scores)), "elapsed_seconds": result["elapsed_seconds"]}
        if spec.method == "cooperative":
            row["holdout_metric"] = "mean team reward on five unseen initial-phase seeds"
            row["holdout_fitness"] = row["replay_mean"]
        elif spec.method == "competitive":
            fixed = competitive_panel(engine.best_genome, engine.validation_panel)
            unseen = competitive_panel(engine.best_genome, heldout_opponents)
            historical = (competitive_panel(engine.best_genome, engine.hall_of_fame)
                          if engine.hall_of_fame else None)
            row.update({"holdout_metric": "worst payoff against independent frozen neural panel",
                        "holdout_fitness": unseen["metrics"]["worst_score"],
                        "holdout_opponent_scores": unseen["metrics"]["opponent_scores"],
                        "fixed_validation_replay": fixed, "historical_opponent_replay": historical,
                        "fixed_validation_sha256": hashlib.sha256(engine.validation_panel.tobytes()).hexdigest(),
                        "game_matches": engine.game_matches,
                        "cycling_warnings": sum(event["cycling_warning"] for event in engine.history)})
        elif spec.method == "poet":
            panel_scores = []
            for environment in common_environments:
                candidates = [float(np.mean([terrain_episode(pair.genome, environment, seed=seed)["fitness"]
                                             for seed in heldout_seeds])) for pair in engine.pairs]
                panel_scores.append(candidates)
            row.update({"holdout_metric": "mean of best active-controller reward on each fixed heldout environment",
                        "holdout_fitness": float(np.mean([max(scores) for scores in panel_scores])),
                        "common_panel_scores_by_environment_and_controller": panel_scores,
                        "common_panel_all_controller_mean": float(np.mean(panel_scores)),
                        "environments_admitted": len(engine.ancestry), "active_pairs": len(engine.pairs),
                        "direct_transfers": engine.transfer_attempts, "adapted_transfers": engine.adapted_transfer_attempts,
                        "accepted_transfers": engine.accepted_transfers,
                        "heldout_evaluation_count": 4 * len(engine.pairs) * len(heldout_seeds)})
        elif spec.method == "surrogate":
            holdout = [float(prescription_episode(engine.best_genome, np.random.default_rng(seed).uniform(-1, 1, 129))["fitness"])
                       for seed in heldout_seeds]
            row.update({"holdout_metric": "mean true reward on unseen random context sets",
                        "holdout_fitness": float(np.mean(holdout)), "unseen_context_scores": holdout,
                        "predicted_evaluations": engine.predicted_evaluations,
                        "true_policy_evaluations": engine.true_policy_evaluations,
                        "true_outcome_queries": engine.true_outcome_queries,
                        "holdout_outcome_queries": 129 * len(heldout_seeds)})
        retain_run(path, output / "runs" / key)
        records.append(row)
        with (output / "runs.jsonl").open("a") as stream:
            stream.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
        if spec.seed == 0 and name in ("cooperative", "competitive", "poet", "surrogate"):
            selected = output / "selected_runs" / name
            selected.mkdir(parents=True)
            for filename in ("manifest.json", "status.json", "checkpoint.pkl", "checkpoint.sha256", f"replay-{spec.seed}.json"):
                shutil.copy2(path / filename, selected / filename)
            with gzip.open(selected / "events.jsonl.gz", "wb") as stream:
                stream.write((path / "events.jsonl").read_bytes())
        print(json.dumps({k: row[k] for k in ("condition", "search_seed", "generation", "committed_evaluations", "holdout_fitness")}), flush=True)

    aggregate = {}
    for name in names:
        rows = [row for row in records if row["condition"] == name]
        values = [row["holdout_fitness"] for row in rows]
        aggregate[name] = {"seeds": [row["search_seed"] for row in rows], "metric": rows[0]["holdout_metric"],
                           "values": values, "mean": float(np.mean(values)), "sample_std": float(np.std(values, ddof=1)),
                           "replay_means": [row["replay_mean"] for row in rows],
                           "committed_evaluations": [row["committed_evaluations"] for row in rows]}
    write_json(output / "aggregate.json", aggregate)
    print(json.dumps({"complete": str(output), "runs": len(records)}), flush=True)


if __name__ == "__main__":
    main()
