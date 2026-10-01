"""Publishing evidence must retain a runnable source snapshot and raw results."""
import gzip
import importlib.util
import os
from pathlib import Path
import subprocess
import sys


def protocol():
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts/ecology_acceptance.py"
    spec = importlib.util.spec_from_file_location("ecology_acceptance_protocol", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return root, module


def test_frozen_ecology_runtime_imports_in_isolation(tmp_path):
    root, module = protocol()
    frozen = tmp_path / "neuroevolution_lab"
    module.freeze_source(root, frozen)
    env = {**os.environ, "PYTHONPATH": str(tmp_path)}
    result = subprocess.run(
        [sys.executable, "-c", "import neuroevolution_lab.runtime as r; print(r.__file__)"],
        env=env, cwd=tmp_path, capture_output=True, text=True, check=True,
    )
    assert Path(result.stdout.strip()) == frozen / "runtime.py"


def test_retained_run_preserves_candidates_and_journal_bytes(tmp_path):
    _, module = protocol()
    source = tmp_path / "source"
    source.mkdir()
    journal = b'{"event":"evaluation_finished","result":{"fitness":0.75}}\n'
    (source / "events.jsonl").write_bytes(journal)
    (source / "checkpoint.pkl").write_bytes(b"opaque trusted-local checkpoint")
    module.retain_run(source, tmp_path / "retained")
    assert gzip.decompress((tmp_path / "retained/events.jsonl.gz").read_bytes()) == journal
    assert (tmp_path / "retained/checkpoint.pkl").read_bytes() == (source / "checkpoint.pkl").read_bytes()
