"""A pausing host-agent bridge and explicitly configured model endpoints."""
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlparse
import httpx
from .runtime import PendingModel, BudgetExceeded, atomic_json, encoded

def complete(ctx, messages, key):
    access = ctx.spec.model
    if access.provider == "disabled": raise ValueError("This experiment requires an explicitly configured model or bridge")
    request_id = hashlib.sha256(encoded({"key":key,"model":access.model,"messages":messages}).encode()).hexdigest()[:24]
    folder = ctx.path / "model_requests"
    folder.mkdir(exist_ok=True)
    response_path = folder / f"{request_id}.response.json"
    request_path = folder / f"{request_id}.request.json"
    if response_path.exists():
        return json.loads(response_path.read_text())["text"]
    remaining_seconds=ctx.spec.budget.wall_seconds-ctx.elapsed
    if remaining_seconds<=0: raise BudgetExceeded("Wall-clock budget exhausted before model request")
    existing = list(folder.glob("*.request.json"))
    if not request_path.exists():
        if len(existing) >= ctx.spec.budget.max_model_calls: raise BudgetExceeded("Model-call budget exhausted")
        atomic_json(request_path,{"id":request_id,"key":key,"model":access.model,"messages":messages,"max_output_tokens":access.max_output_tokens,"status":"pending","provider":access.provider})
    if access.provider == "bridge": raise PendingModel(f"Model response requested: {request_id}; use bridge next/submit")
    # Do not retry a request with an uncertain remote outcome automatically.
    request = json.loads(request_path.read_text())
    if request["status"] == "dispatched": raise RuntimeError("Remote outcome unknown; inspect request before any retry")
    local = urlparse(access.base_url).hostname in ("localhost","127.0.0.1","::1")
    observed_cost = sum(json.loads(p.read_text()).get("cost_usd",0) for p in folder.glob("*.response.json"))
    reserve = 0.0
    if not local:
        # UTF-8 bytes give a conservative input-token allowance for ordinary text.
        input_allowance = len(encoded(messages).encode("utf8")) + 256
        reserve = (input_allowance * access.input_usd_per_million + access.max_output_tokens*access.output_usd_per_million)/1e6
        if observed_cost + reserve > access.max_cost_usd: raise BudgetExceeded("Insufficient hosted-model budget for next request")
    request["status"] = "dispatched"; request["reserved_cost_usd"] = reserve
    atomic_json(request_path,request)
    headers = {}
    secret = os.environ.get(access.api_key_env)
    if secret: headers["Authorization"] = "Bearer " + secret
    response = httpx.post(access.base_url.rstrip("/")+"/chat/completions",headers=headers,
        json={"model":access.model,"messages":messages,"temperature":0,"max_tokens":access.max_output_tokens},timeout=min(access.timeout_seconds,remaining_seconds))
    response.raise_for_status()
    body = response.json()
    text = body["choices"][0]["message"]["content"]
    if not isinstance(text,str): raise ValueError("Model returned non-text content")
    usage = body.get("usage")
    if not local and not usage: raise ValueError("Hosted endpoint omitted usage; refusing further unpriced calls")
    if usage is not None and (not isinstance(usage,dict) or any(type(usage.get(k)) is not int or usage[k]<0 for k in ("prompt_tokens","completion_tokens"))):
        raise ValueError("Endpoint usage requires nonnegative integer prompt/completion token counts")
    cost = 0 if local else (usage["prompt_tokens"]*access.input_usd_per_million+usage["completion_tokens"]*access.output_usd_per_million)/1e6
    atomic_json(response_path,{"id":request_id,"text":text,"provenance":{"provider":"endpoint","model":body.get("model",access.model)},"usage":usage,"cost_usd":cost})
    return text

def next_request(path):
    folder = Path(path) / "model_requests"
    requests = sorted(folder.glob("*.request.json"),key=lambda p:p.stat().st_mtime_ns)
    for file in requests:
        if not file.with_name(file.name.replace(".request.",".response.")).exists():
            return json.loads(file.read_text())
    return None

def submit_response(path, request_id, text, provenance):
    if not request_id.isalnum() or len(request_id)!=24: raise ValueError("Invalid request ID")
    folder = Path(path)/"model_requests"
    request = folder/f"{request_id}.request.json"
    response = folder/f"{request_id}.response.json"
    if not request.exists(): raise ValueError("Unknown model request")
    if json.loads(request.read_text())["provider"] != "bridge": raise ValueError("Only bridge requests accept manual submissions")
    if response.exists(): raise ValueError("Response is immutable; it already exists")
    if not text.strip() or not provenance.strip(): raise ValueError("Response text and truthful model provenance are required")
    atomic_json(response,{"id":request_id,"text":text,"provenance":{"provider":"bridge","source":provenance},"usage":None,"cost_usd":0,"usage_note":"Host usage unavailable; zero records no new endpoint charge, not zero inference cost"})
