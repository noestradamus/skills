"""Explicit supported method compositions; no silent algorithm substitution."""
CONTROLLER_TARGETS = {"xor", "cartpole", "navigation", "deceptive_navigation", "deceptive_maze", "CartPole-v1", "cart_pole"}
TARGETS = {
    **{m: CONTROLLER_TARGETS for m in ("fixed_controller", "random_search", "ga", "es", "cma_es", "nsga2", "novelty", "nslc", "map_elites", "neat", "hyperneat")},
    "cppn": {"pattern"}, "modular_nas": {"continuous_xor"},
    "gradient_refinement": {"sine_regression"}, "evolutionary_initialization": {"sine_task_family"},
    "evolved_plasticity": {"associative_memory"}, "erl": {"tracking_control"},
    "differentiable_qd": {"differentiable_arm"},
    "model_merging": {"tiny_autoregressive"}, "parameter_evolution": {"tiny_autoregressive"},
    "cooperative": {"cooperative-tracking"}, "competitive": {"competitive-rps"},
    "poet": {"terrain-tracking"}, "surrogate": {"surrogate-control"},
    **{m: {"arithmetic_tools"} for m in ("llm_prompt", "llm_workflow", "llm_program", "llm_mutation", "llm_crossover", "neural_router", "fixed_agent", "random_agent", "greedy_agent", "llm_holdout")},
}
LEARNING = {"gradient_refinement", "evolutionary_initialization", "erl", "modular_nas", "model_merging", "parameter_evolution"}
TORCH_METHODS = {"fixed_controller","random_search","ga","es","cma_es","nsga2","novelty","nslc","map_elites",
                 "neat","cppn","hyperneat","modular_nas","gradient_refinement","evolutionary_initialization",
                 "evolved_plasticity","erl","differentiable_qd","model_merging","parameter_evolution"}

def validate_compatibility(spec):
    if spec.method not in TARGETS:
        raise ValueError(f"Unknown method {spec.method!r}. Available profiles: {', '.join(sorted(TARGETS))}")
    if spec.target not in TARGETS[spec.method]:
        raise ValueError(f"{spec.method} supports {sorted(TARGETS[spec.method])}, not {spec.target!r}. Add and test an evaluator adapter to extend this profile.")
    if spec.compute.backend == "reference" and spec.compute.device != "cpu":
        raise ValueError("The reference backend executes on CPU. Select compute.backend='torch' for accelerator execution.")
    if spec.compute.backend == "torch" and spec.method not in TORCH_METHODS:
        raise ValueError(f"{spec.method} has no local torch execution backend. LLM inference hardware is selected at its model endpoint; ecology currently uses the CPU reference backend.")
    from .devices import resolve_device
    device=resolve_device(spec.compute)
    if spec.learning and spec.method not in LEARNING:
        raise ValueError(f"{spec.method} does not support gradient-learning composition. Use an explicit learning profile; options would otherwise be ignored.")
    if "inheritance" in spec.learning and spec.method not in {"gradient_refinement", "evolutionary_initialization"}:
        raise ValueError(f"{spec.method} has its own documented state semantics; selectable inheritance is only supported for gradient_refinement and evolutionary_initialization")
    if spec.method.startswith("llm_") or spec.method in {"neural_router", "fixed_agent", "random_agent", "greedy_agent"}:
        if spec.model.provider == "disabled":
            raise ValueError("This method requires model.provider='bridge' or a configured endpoint")
    return {"method": spec.method, "target": spec.target, "compatible": True,
            "execution_workers": 1,"compute":spec.compute.model_dump(),"resolved_device":str(device),
            "note": "One orchestration process; torch profiles batch supported numerical work. workers is an upper bound."}
