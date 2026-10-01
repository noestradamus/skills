"""Validated, provider-neutral experiment contracts."""
from pathlib import Path
from typing import Any, Literal
import tomllib
from urllib.parse import urlparse
from pydantic import BaseModel, ConfigDict, Field, model_validator

class Compute(BaseModel):
    model_config = ConfigDict(extra="forbid")
    device: str = Field(default="cpu", pattern=r"^(cpu|mps|cuda(?::[0-9]+)?)$")
    backend: Literal["reference", "torch"] = "reference"
    batch_size: int = Field(default=32, ge=1, le=4096)

class Budget(BaseModel):
    model_config = ConfigDict(extra="forbid")
    max_evaluations: int = Field(default=512, ge=1)
    wall_seconds: float = Field(default=600, gt=0)
    workers: int = Field(default=1, ge=1, le=4)
    max_model_calls: int = Field(default=32, ge=0)

class ModelAccess(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: Literal["disabled", "bridge", "endpoint"] = "disabled"
    model: str = "host-agent"
    base_url: str = "http://127.0.0.1:8000/v1"
    api_key_env: str = "NEUROEVO_API_KEY"
    max_output_tokens: int = Field(default=512, ge=1)
    max_cost_usd: float = Field(default=0, ge=0)
    input_usd_per_million: float | None = Field(default=None, ge=0)
    output_usd_per_million: float | None = Field(default=None, ge=0)
    timeout_seconds: float = Field(default=60, gt=0)

    @model_validator(mode="after")
    def spending(self):
        if self.provider == "endpoint":
            u = urlparse(self.base_url)
            if u.scheme not in ("http", "https") or u.username or u.password:
                raise ValueError("Use an HTTP(S) endpoint without credentials in its URL")
            if u.hostname not in ("localhost", "127.0.0.1", "::1"):
                if self.max_cost_usd <= 0 or self.input_usd_per_million is None or self.output_usd_per_million is None:
                    raise ValueError("Hosted endpoints require a positive spending limit and explicit token prices")
        return self

class ExperimentSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = "experiment"
    method: str
    target: str
    seed: int = Field(default=0, ge=0)
    population_size: int = Field(default=16, ge=2)
    generations: int = Field(default=8, ge=1)
    parameters: dict[str, Any] = Field(default_factory=dict)
    learning: dict[str, Any] = Field(default_factory=dict)
    budget: Budget = Field(default_factory=Budget)
    model: ModelAccess = Field(default_factory=ModelAccess)
    compute: Compute = Field(default_factory=Compute)

def load_spec(path: str | Path) -> ExperimentSpec:
    with Path(path).open("rb") as f:
        return ExperimentSpec.model_validate(tomllib.load(f))
