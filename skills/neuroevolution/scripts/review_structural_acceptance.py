"""Freeze fresh demonstrations after correcting the paper-oriented NEAT profile."""
import argparse
import hashlib
from pathlib import Path

from neuroevolution_lab.config import load_spec
from neuroevolution_lab.runtime import execute, replay_run, atomic_json, environment_identity
from neuroevolution_lab.reporting import report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    names = ["neat-xor", "neat-cartpole", "cppn-pattern", "hyperneat-xor", "hyperneat-navigation"]
    specs = {name: load_spec(root / "examples" / f"{name}.toml") for name in names}
    args.out.mkdir(parents=True, exist_ok=False)
    atomic_json(args.out / "protocol.json", {
        "purpose": "Corrected paper-profile-v2 operation and unseen-condition replay; no comparative claim",
        "environment": environment_identity(),
        "protocol_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "specifications": {name: spec.model_dump() for name, spec in specs.items()},
        "replay_seed": 10000,
        "frozen_before_execution": True,
    })
    results = []
    for name, spec in specs.items():
        path = args.out / name
        status = execute(spec, path)
        if status["status"] != "completed":
            raise RuntimeError(f"{name}: {status['status']}: {status.get('detail')}")
        if status["summary"]["evolution_profile"] != "paper-profile-v2":
            raise RuntimeError("Fresh run used a legacy profile")
        replay = replay_run(path, seed=10000)
        report(path)
        row = {"name": name, "status": status["status"], "evaluations": status["evaluations"],
               "evolution_profile": status["summary"]["evolution_profile"],
               "summary": status["summary"], "replay": replay}
        results.append(row)
        atomic_json(args.out / "results.json", results)
        print(name, status["status"], status["evaluations"], flush=True)


if __name__ == "__main__":
    main()
