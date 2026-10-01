"""Explicit execution devices. An unavailable accelerator never silently falls back."""
from __future__ import annotations
import os
import torch


def resolve_device(compute=None) -> torch.device:
    if hasattr(compute, "model_dump"):
        compute = compute.model_dump()
    name = (compute or {}).get("device", "cpu")
    try:
        device = torch.device(name)
    except (RuntimeError, ValueError) as exc:
        raise ValueError(f"Invalid compute device {name!r}") from exc
    if device.type == "cpu" and device.index is None:
        return device
    if device.type == "mps" and device.index is None:
        if not torch.backends.mps.is_available():
            raise ValueError("MPS was requested but is unavailable in this process. Check Apple GPU access and the PyTorch build; CPU fallback is not automatic.")
        if os.environ.get("PYTORCH_ENABLE_MPS_FALLBACK") == "1":
            raise ValueError("Unset PYTORCH_ENABLE_MPS_FALLBACK for measured MPS experiments; unsupported operators must fail explicitly.")
        return device
    if device.type == "cuda":
        if not torch.cuda.is_available():
            raise ValueError("CUDA was requested but is unavailable. Install the locked CUDA environment and check the NVIDIA driver/GPU; CPU fallback is not automatic.")
        index = torch.cuda.current_device() if device.index is None else device.index
        if index >= torch.cuda.device_count():
            raise ValueError(f"CUDA device index {index} is unavailable")
        return torch.device("cuda", index)
    raise ValueError("Supported devices are cpu, mps, cuda, and cuda:N")


def synchronize(device):
    device = torch.device(device)
    if device.type == "cuda":
        torch.cuda.synchronize(device)
    elif device.type == "mps":
        torch.mps.synchronize()


def memory_stats(device):
    device = torch.device(device)
    if device.type == "cuda":
        return {"allocated_bytes":torch.cuda.memory_allocated(device),
                "reserved_bytes":torch.cuda.memory_reserved(device),
                "peak_allocated_bytes":torch.cuda.max_memory_allocated(device),
                "peak_scope":"process allocator since its last peak reset; not necessarily this experiment"}
    if device.type == "mps":
        return {"allocated_bytes":torch.mps.current_allocated_memory(),
                "driver_allocated_bytes":torch.mps.driver_allocated_memory(),
                "recommended_max_bytes":torch.mps.recommended_max_memory(),
                "peak_allocated_bytes":None}
    return {"allocated_bytes":None,"peak_allocated_bytes":None,
            "note":"CPU tensor allocator and MPS peak allocation are not measured by this interface."}


def device_identity(device="cpu"):
    device = torch.device(device)
    value = {"device":str(device),"torch":torch.__version__,"cuda_build":torch.version.cuda}
    if device.type == "cuda":
        properties = torch.cuda.get_device_properties(device)
        value.update(name=properties.name,total_memory_bytes=properties.total_memory,
                     capability=list(torch.cuda.get_device_capability(device)))
    elif device.type == "mps":
        value.update(name="Apple Metal GPU",mps_built=torch.backends.mps.is_built())
    else:
        value["name"] = "CPU"
    return value


def capabilities():
    cuda = torch.cuda.is_available()
    return {"cpu":True,"mps":{"built":torch.backends.mps.is_built(),"available":torch.backends.mps.is_available()},
            "cuda":{"build":torch.version.cuda,"available":cuda,
                    "devices":[device_identity(f"cuda:{i}") for i in range(torch.cuda.device_count())] if cuda else []},
            "note":"Availability is process-specific; it does not establish kernel correctness or speedup."}
