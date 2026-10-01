"""Journaled evaluation and resumable trusted-local experiment execution.

Checkpoints contain Python backend objects. Only open checkpoints produced in a
trusted local workspace; they are not an interchange format for third parties.
"""
from __future__ import annotations
import hashlib
import gzip
import importlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import pickle
import random
import time
from typing import Any
import numpy as np
from .config import ExperimentSpec
from .devices import resolve_device, synchronize, memory_stats, device_identity

class BudgetExceeded(RuntimeError): pass
class PendingModel(RuntimeError): pass

def plain(obj: Any):
    if isinstance(obj, np.ndarray): return obj.tolist()
    if isinstance(obj, np.generic): return obj.item()
    if isinstance(obj, Path): return str(obj)
    if hasattr(obj, "detach"): return obj.detach().cpu().tolist()
    if isinstance(obj, dict): return {str(k): plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)): return [plain(x) for x in obj]
    return obj

def encoded(obj: Any) -> str:
    return json.dumps(plain(obj), sort_keys=True, allow_nan=False, separators=(",", ":"))

def atomic_json(path: Path, data: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(encoded(data) + "\n")
    os.replace(temp, path)

def read_events(path: Path) -> list[dict]:
    if not path.exists() and path.with_suffix(path.suffix+".gz").exists():
        # Expand a preserved evidence journal before any resume appends to it.
        data=gzip.decompress(path.with_suffix(path.suffix+".gz").read_bytes())
        temp=path.with_suffix(path.suffix+".tmp"); temp.write_bytes(data); os.replace(temp,path)
    if not path.exists(): return []
    rows = []
    lines = path.read_text().splitlines()
    for i, line in enumerate(lines):
        try: rows.append(json.loads(line))
        except json.JSONDecodeError:
            if i != len(lines) - 1: raise ValueError(f"Corrupt journal at line {i+1}")
            # A crash can leave a truncated final write; preserve the bad bytes.
            path.with_suffix(".truncated").write_text(line)
            path.write_text("\n".join(lines[:i]) + ("\n" if i else ""))
    return rows

def registry() -> dict:
    methods = {}
    for name in ("search", "structural", "learning", "models", "ecology", "llm"):
        try: module = importlib.import_module(f"neuroevolution_lab.{name}")
        except ModuleNotFoundError as e:
            if e.name == f"neuroevolution_lab.{name}": continue
            raise
        overlap = methods.keys() & getattr(module, "METHODS", {}).keys()
        if overlap: raise ValueError(f"Duplicate method identifiers: {overlap}")
        methods.update(getattr(module, "METHODS", {}))
    return methods

def build_engine(spec: ExperimentSpec):
    from .compatibility import validate_compatibility
    validate_compatibility(spec)
    methods = registry()
    if spec.method not in methods:
        raise ValueError(f"Unknown method {spec.method!r}; supported: {', '.join(sorted(methods))}")
    return methods[spec.method](spec.model_dump())

class Context:
    def __init__(self, path: Path, spec: ExperimentSpec, cursor=0, elapsed=0.0, *, start=None):
        self.path, self.spec, self.cursor = path, spec, cursor
        self.device = resolve_device(spec.compute)
        self.start = time.monotonic() if start is None else start
        self.rows = read_events(path / "events.jsonl")
        # A hard exit can leave status behind the durable journal. Historical
        # journals have no active clock field; never infer it from wall timestamps,
        # which would charge time waiting for a bridge response or a later resume.
        journal_elapsed = max((r.get("active_elapsed_seconds", 0.0) for r in self.rows), default=0.0)
        self.prior_elapsed = max(elapsed, journal_elapsed)
        self.started = {r["id"]:r for r in self.rows if r.get("event") == "evaluation_started"}
        self.results = {r["id"]:r for r in self.rows if r.get("event") == "evaluation_finished"}
        self.step_cursor = cursor
        self.event_ids = {r.get("event_id") for r in self.rows if r.get("event_id")}
    @property
    def elapsed(self): return self.prior_elapsed + time.monotonic() - self.start
    @property
    def eval_count(self): return len(self.started)
    @property
    def remaining(self): return max(0, self.spec.budget.max_evaluations-self.eval_count)
    def record(self, event: dict):
        record = {"time":time.time(), **plain(event), "active_elapsed_seconds":self.elapsed}
        if event.get("event") not in {"evaluation_started","evaluation_finished"}:
            identity=hashlib.sha256(encoded({"step_cursor":self.step_cursor,"data":event}).encode()).hexdigest()
            if identity in self.event_ids: return
            record["event_id"]=identity; self.event_ids.add(identity)
        with (self.path / "events.jsonl").open("a") as f:
            f.write(encoded(record) + "\n"); f.flush(); os.fsync(f.fileno())
        self.rows.append(record)
    def evaluate(self, genome, fn, *, label="", kind="observed"):
        evaluation_id = self.cursor
        self.cursor += 1
        genome = plain(genome)
        digest = hashlib.sha256(encoded({"genome":genome,"label":label,"kind":kind}).encode()).hexdigest()
        old = self.started.get(evaluation_id)
        if old and old["digest"] != digest:
            raise RuntimeError(f"Non-reproducible replay at evaluation {evaluation_id}; refusing stale cached evidence")
        if evaluation_id in self.results:
            saved = self.results[evaluation_id]
            if saved["status"] == "failed": raise RuntimeError(saved["error"])
            return saved["result"]
        if self.elapsed >= self.spec.budget.wall_seconds: raise BudgetExceeded("Wall-clock budget exhausted")
        if not old:
            if not self.remaining: raise BudgetExceeded("Evaluation budget exhausted")
            old = {"event":"evaluation_started","id":evaluation_id,"digest":digest,"genome":genome,"label":label,"kind":kind}
            self.record(old); self.started[evaluation_id] = old
        synchronize(self.device)
        t = time.monotonic()
        try:
            result = plain(fn())
            synchronize(self.device)
            if not isinstance(result, dict) or not isinstance(result.get("fitness"), (float,int)):
                raise ValueError("Evaluator must return a mapping with numeric fitness")
            if not math.isfinite(result["fitness"]): raise ValueError("Fitness must be finite")
            result.setdefault("descriptor", []); result.setdefault("objectives", [result["fitness"]])
            result.setdefault("constraints", True); result.setdefault("metrics", {})
            result["measurement_kind"] = kind
            encoded(result)  # Reject nonfinite numbers and nonserializable evidence.
        except (PendingModel, BudgetExceeded):
            self.cursor -= 1
            raise
        except Exception as e:
            row = {"event":"evaluation_finished","id":evaluation_id,"status":"failed","error":f"{type(e).__name__}: {e}","seconds":time.monotonic()-t}
            self.record(row); self.results[evaluation_id] = row
            raise
        row = {"event":"evaluation_finished","id":evaluation_id,"status":"ok","result":result,"seconds":time.monotonic()-t}
        self.record(row); self.results[evaluation_id] = row
        return result

    def evaluate_batch(self, genomes, fn, *, labels=None, kind="observed"):
        """Dispatch before computing; fn receives only indices without cached results.

        One callback performs the tensor batch. Each candidate retains its own
        identity, budget charge and result. A partially affordable batch is
        measured and committed before budget exhaustion propagates to the runner.
        """
        genomes = list(genomes)
        labels = [""] * len(genomes) if labels is None else list(labels)
        if len(labels) != len(genomes):
            raise ValueError("Batch labels and genomes must have the same length")
        initial_cursor = self.cursor
        prepared = []
        for i, (genome, label) in enumerate(zip(genomes, labels)):
            genome = plain(genome)
            digest = hashlib.sha256(encoded({"genome":genome,"label":label,"kind":kind}).encode()).hexdigest()
            old = self.started.get(initial_cursor+i)
            if old and old["digest"] != digest:
                raise RuntimeError(f"Non-reproducible replay at evaluation {initial_cursor+i}; refusing stale cached evidence")
            prepared.append((genome,label,digest))
        output = [None]*len(genomes)
        pending, ids, limit = [], [], None
        for i,(genome,label,digest) in enumerate(prepared):
            evaluation_id = initial_cursor+i
            if evaluation_id in self.results:
                saved = self.results[evaluation_id]
                if saved["status"] == "failed":
                    raise RuntimeError(saved["error"])
                output[i] = saved["result"]
                self.cursor += 1
                continue
            if self.elapsed >= self.spec.budget.wall_seconds:
                limit = "Wall-clock budget exhausted"; break
            if evaluation_id not in self.started:
                if not self.remaining:
                    limit = "Evaluation budget exhausted"; break
                row={"event":"evaluation_started","id":evaluation_id,"digest":digest,
                     "genome":genome,"label":label,"kind":kind}
                self.record(row); self.started[evaluation_id]=row
            pending.append(i); ids.append(evaluation_id); self.cursor += 1
        if pending:
            self.record({"event":"batch_started","evaluation_ids":ids,"device":str(self.device)})
            synchronize(self.device)
            start = time.monotonic()
            try:
                values = list(fn(pending))
                synchronize(self.device)
                if len(values) != len(pending):
                    raise ValueError("Batched evaluator returned the wrong number of results")
            except (PendingModel, BudgetExceeded):
                self.cursor = initial_cursor
                raise
            except Exception as exc:
                seconds=time.monotonic()-start
                for evaluation_id in ids:
                    row={"event":"evaluation_finished","id":evaluation_id,"status":"failed",
                         "error":f"{type(exc).__name__}: {exc}","seconds":seconds/len(ids),"batch_seconds":seconds}
                    self.record(row); self.results[evaluation_id]=row
                raise
            seconds=time.monotonic()-start
            errors=[]
            for i,evaluation_id,value in zip(pending,ids,values):
                row={"event":"evaluation_finished","id":evaluation_id,
                     "seconds":seconds/len(ids),"batch_seconds":seconds}
                try:
                    value=plain(value)
                    if not isinstance(value,dict) or not isinstance(value.get("fitness"),(float,int)) or not math.isfinite(value["fitness"]):
                        raise ValueError("Evaluator must return a mapping with finite numeric fitness")
                    value.setdefault("descriptor",[]); value.setdefault("objectives",[value["fitness"]])
                    value.setdefault("constraints",True); value.setdefault("metrics",{})
                    value["measurement_kind"]=kind; encoded(value)
                    row.update(status="ok",result=value); output[i]=value
                except Exception as exc:
                    row.update(status="failed",error=f"{type(exc).__name__}: {exc}"); errors.append(exc)
                self.record(row); self.results[evaluation_id]=row
            self.record({"event":"batch_finished","evaluation_ids":ids,"device":str(self.device),
                         "synchronized_seconds":seconds,"memory":memory_stats(self.device),
                         "timing_note":"Per-candidate seconds apportions shared batch time; it is not isolated latency."})
            if errors:
                raise errors[0]
        if limit:
            raise BudgetExceeded(limit)
        return output

def rng_state(device="cpu"):
    import torch
    device=torch.device(device)
    accelerator=None
    if device.type=="cuda":
        accelerator={"device":str(device),"state":torch.cuda.get_rng_state(device)}
    elif device.type=="mps":
        accelerator={"device":"mps","state":torch.mps.get_rng_state()}
    return (random.getstate(), np.random.get_state(), torch.get_rng_state(),accelerator)

def restore_rng(state):
    import torch
    random.setstate(state[0]); np.random.set_state(state[1]); torch.set_rng_state(state[2])
    if len(state)>3 and state[3] is not None:
        accelerator=state[3]; device=resolve_device({"device":accelerator["device"]})
        if device.type=="cuda": torch.cuda.set_rng_state(accelerator["state"].cpu(),device)
        elif device.type=="mps": torch.mps.set_rng_state(accelerator["state"].cpu())

def save_checkpoint(path, engine, cursor, rng):
    payload = pickle.dumps({"engine":engine,"cursor":cursor,"rng":rng}, protocol=5)
    # One atomic file carries payload and its checksum. The sidecar is informational.
    data = b"NEUROEVO1\n" + hashlib.sha256(payload).hexdigest().encode() + b"\n" + payload
    temp = path / "checkpoint.tmp"
    temp.write_bytes(data); os.replace(temp, path / "checkpoint.pkl")
    (path / "checkpoint.sha256").write_text(hashlib.sha256(data).hexdigest())

def load_checkpoint(path):
    data = (path / "checkpoint.pkl").read_bytes()
    if data.startswith(b"NEUROEVO1\n"):
        _,checksum,payload=data.split(b"\n",2)
        if hashlib.sha256(payload).hexdigest().encode()!=checksum: raise ValueError("Checkpoint checksum mismatch")
        return pickle.loads(payload)
    # Older evidence checkpoints retain their original two-file hashes.
    if hashlib.sha256(data).hexdigest() != (path / "checkpoint.sha256").read_text().strip():
        raise ValueError("Checkpoint checksum mismatch")
    return pickle.loads(data)  # Trusted local checkpoints only; see module contract.

def environment_identity(device="cpu",backend="reference"):
    import platform
    import sys
    versions = {}
    for name in ("neuroevolution","numpy","scipy","neat-python","cma","ribs","pymoo","torch","gymnasium"):
        try: versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError: versions[name] = "missing"
    source = Path(__file__).parent
    source_hash = hashlib.sha256(b"".join(p.name.encode()+p.read_bytes() for p in sorted(source.glob("*.py")))).hexdigest()
    root=source.parent.parent
    locks={}
    active=None
    for name,folder in (("default",root),("cuda",root/"environments"/"cuda")):
        lock=folder/"uv.lock"
        if lock.exists():
            locks[name]={"path":str(lock.relative_to(root)),"sha256":hashlib.sha256(lock.read_bytes()).hexdigest()}
            if Path(sys.prefix).resolve()==(folder/".venv").resolve(): active=name
    return {"python":platform.python_version(),"platform":platform.platform(),"packages":versions,
            "source_sha256":source_hash,"lock_sha256":locks[active]["sha256"] if active else None,
            "active_environment":active,"dependency_locks":locks,
            "environment_note":"Active lock is identified by the standard environment path; custom external environments retain package versions but no asserted active lock.",
            "execution_workers":1,"device":str(device),"backend":backend,"accelerator":device_identity(device)}

def execute(spec: ExperimentSpec, path: str | Path, *, resume=False):
    execution_start = time.monotonic()
    import torch
    torch.set_num_threads(1)
    from .compatibility import validate_compatibility
    validate_compatibility(spec)
    device=resolve_device(spec.compute)
    path = Path(path).resolve()
    if resume:
        manifest = json.loads((path / "manifest.json").read_text())
        original = ExperimentSpec.model_validate(manifest["spec"])
        if spec.model_dump() != original.model_dump(): raise ValueError("Resume must preserve the original experiment specification")
        cp = load_checkpoint(path); engine = cp["engine"]; restore_rng(cp["rng"])
        cursor = cp["cursor"]
        status_path = path / "status.json"
        elapsed = json.loads(status_path.read_text()).get("elapsed_seconds",0) if status_path.exists() else 0.0
    else:
        if path.exists() and any(path.iterdir()): raise ValueError("Run directory must be new or empty")
        path.mkdir(parents=True,exist_ok=True)
        random.seed(spec.seed); np.random.seed(spec.seed); torch.manual_seed(spec.seed)
        engine = build_engine(spec); cursor = 0; elapsed = 0
        atomic_json(path / "manifest.json", {"spec":spec.model_dump(),"environment":environment_identity(device,spec.compute.backend),"created":time.time(),"checkpoint_trust":"local-only"})
        save_checkpoint(path,engine,cursor,rng_state(device))
    ctx = Context(path,spec,cursor,elapsed,start=execution_start)
    # Make the initial checkpoint resumable before the first candidate dispatch.
    # Initialization and restore work count toward this invocation's active time.
    atomic_json(path / "status.json",{"status":"running","evaluations":ctx.eval_count,"elapsed_seconds":ctx.elapsed})
    ctx.record({"event":"execution_identity","resumed":resume,"source":environment_identity(device,spec.compute.backend)})
    status, detail = "completed", None
    while not engine.done:
        if ctx.elapsed >= spec.budget.wall_seconds:
            status,detail = "budget_exhausted","Wall-clock budget exhausted"; break
        before = pickle.dumps((engine,ctx.cursor,rng_state(device)),protocol=5)
        ctx.step_cursor=ctx.cursor
        try:
            engine.step(ctx)
            synchronize(device)
            save_checkpoint(path,engine,ctx.cursor,rng_state(device))
        except (PendingModel,BudgetExceeded,KeyboardInterrupt) as e:
            engine,cursor,rng = pickle.loads(before); restore_rng(rng)
            status = "waiting_for_model" if isinstance(e,PendingModel) else "interrupted" if isinstance(e,KeyboardInterrupt) else "budget_exhausted"
            detail = str(e)
            break
        except Exception as e:
            engine,cursor,rng = pickle.loads(before); restore_rng(rng)
            status,detail = "failed",f"{type(e).__name__}: {e}"
            break
        atomic_json(path / "status.json",{"status":"running","evaluations":ctx.eval_count,"elapsed_seconds":ctx.elapsed})
    result = {"status":status,"detail":detail,"evaluations":ctx.eval_count,"elapsed_seconds":ctx.elapsed,"method":spec.method,"target":spec.target,"compute":spec.compute.model_dump(),"device_memory":memory_stats(device),"summary":plain(engine.summary())}
    atomic_json(path / "status.json",result)
    if status!="waiting_for_model":
        from .reporting import report
        try:
            result["report"]=report(path)["report"]
        except Exception as e:
            result["report_error"]=f"{type(e).__name__}: {e}"
        atomic_json(path / "status.json",result)
    return result

def resume_run(path):
    path = Path(path)
    spec = ExperimentSpec.model_validate(json.loads((path / "manifest.json").read_text())["spec"])
    return execute(spec,path,resume=True)

def replay_run(path, seed=10000):
    path = Path(path)
    manifest=json.loads((path/"manifest.json").read_text())
    resolve_device(manifest["spec"].get("compute",{}))
    cp = load_checkpoint(path)
    result = plain(cp["engine"].replay(seed=seed))
    atomic_json(path / f"replay-{seed}.json", {"seed":seed,"result":result,"kind":"direct_replay"})
    return result
