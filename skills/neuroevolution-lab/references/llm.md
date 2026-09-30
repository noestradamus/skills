# Language-model and agent evolution

These profiles evolve executable systems around a fixed model. The model proposes structured variations and responds to tasks; an independent exact evaluator scores the executed result. The bundled domain uses generated integer arithmetic tool tasks with held-out cases. It is an inspectable live-model experiment, not a general agent benchmark.

## Representations and operators

An agent genome contains a prompt and an ordered bounded list of typed nodes. One `model` node starts execution; up to five additional `calculate`/`verify` nodes execute in the declared order. A calculator can materialize a requested tool result; a verifier can reject the current answer. No shell, filesystem or arbitrary tool capability can be introduced through a workflow genome. The arithmetic tool parses a restricted integer AST, never Python eval.

`llm_prompt` fixes the workflow and evolves the prompt. `llm_workflow` evolves both. `llm_mutation` supplies a selected parent to the proposal model; `llm_crossover` supplies two parents with instructions to combine compatible strengths. Parent identities and child genomes are recorded. The first generation is model-generated initialization. Generated variation is validated before execution. Schema violations remain failures; no hidden repair or algorithm substitution occurs.

`neural_router` additionally evolves a three-weight neural gate controlling calculator access from actual task/model-action features. This is a neural controller around a fixed LLM; it changes executed tool use, not base LLM tensors. `llm_program` evolves `solve(a,b,c,d)` Python programs and executes them in Docker. Base language-model tensor evolution and aligned merging are separate `parameter_evolution` / `model_merging` profiles described in learning.md.

Selection retains elites and behavioral cells (tool-use fraction, verification fraction). Occupants are eligible parents. This small explicit archive is a reference variant; general controller MAP-Elites uses pyribs. It is not NEAT and has no neural innovation/speciation semantics. The workflow is deliberately bounded, without arbitrary loops or unconstrained DAG mutation.

The current-best genome is always a parent; other distinct archive/evaluated candidates are sampled with positive eligibility. At least two distinct parents are retained when available, including population size two. [Evolution through Large Models](https://arxiv.org/abs/2206.08896) motivates model-mediated program variation; these small typed-agent profiles are disclosed adaptations, not a reproduction of its robot experiments.

Baselines: `fixed_agent` executes an unchanged instruction/pipeline, `random_agent` requests independent candidates without parents or fitness history, `greedy_agent` revises the best current candidate. Use the same task cases and evaluation budget. Report proposal calls separately: a fixed agent necessarily uses fewer model calls. A comparison is not cost matched merely because candidate counts match.

## Model access

```toml
[model]
provider = "bridge"
model = "host-agent"
max_output_tokens = 512

[budget]
max_evaluations = 8
max_model_calls = 16
wall_seconds = 600
```

For an OpenAI-compatible local endpoint use `provider="endpoint"`, `base_url="http://127.0.0.1:8000/v1"`, and its configured model name. A hosted endpoint also requires `max_cost_usd`, `input_usd_per_million`, and `output_usd_per_million`. Credentials are read from `api_key_env` at dispatch and are never written into requests. Input/output reservation is conservative for ordinary text, but provider billing remains authoritative. Keep provider-side spending controls for hard account-wide caps.

Each request is a JSON file under `RUN/model_requests`. Read exact messages with `bridge next RUN`, generate the response as the operating language model, save its raw text, submit with truthful provenance, then resume. The bridge cannot launch an agent by itself. Preserve request/response identity and usage if available; host-token usage is marked unobservable rather than invented. A script that computes answers is only a protocol fixture, not live language-model evidence.

The solver gets a batch of independent tasks and returns `{"actions":[...]}`. Each action is an integer `answer` or `tool="calculate"` with a literal expression. The evaluator's expected answers are not supplied to proposals or solver messages. The verifier can reject an incorrect answer but does not replace it with the correct answer.

## Holdout and replay

Freeze the selected genome before invoking `evaluate-heldout TRAIN_RUN --out HOLDOUT_RUN --seed 10000 --cases 8`. This produces fresh model requests, scores a fixed candidate once and performs no selection or revision. Program replay executes the saved program on new generated inputs. Plain agent `replay` intentionally reports that fresh model evaluation is required instead of scoring cached text as new inference.

The CLI rejects held-out cases that exactly overlap the training inputs. A host bridge uses the operating model's conversation context; it cannot guarantee isolation from earlier requests. Disclose shared context and repeated manually authored responses. A fresh request is not necessarily unseen to the operating model, and five task seeds do not establish five independent samples of model decoding randomness.

The current examples use small integers and a single known expression family. Ceiling effects are expected. Successful execution, variation and correct tool use are evidence of mechanism operation. Do not infer broad reasoning gains, multi-tool planning, robustness to arbitrary untrusted input, or large-LLM superiority from this domain.
