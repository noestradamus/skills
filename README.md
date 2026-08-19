# Agent Skills

Reusable skills for AI-agent research workflows, engineering practices, and personal automation.

## Available Skills

| Skill | Purpose |
| --- | --- |
| [`fowler-refactoring`](skills/fowler-refactoring/) | Refactor or systematically clean existing code through small verified transformations, evidence-backed dispositions, and proportionate guardrails. |
| [`paradigm-forge`](skills/paradigm-forge/) | Design ambitious, original AI project directions with concrete discovery mechanisms and human judgment. |
| [`pushing-research-frontier`](skills/pushing-research-frontier/) | Plan, execute, and evaluate research intended to surpass the strongest current method. |

## Structure

Each skill is a self-contained package:

```text
skills/
└── skill-name/
    ├── SKILL.md
    ├── agents/
    │   └── openai.yaml
    └── references/
```

Skills may also include `scripts/` or `assets/` when needed.

## Install a Skill for Codex

Copy a skill into your personal Codex skills directory:

```bash
mkdir -p ~/.codex/skills
cp -R skills/<skill-name> ~/.codex/skills/
```

Start a new Codex session if the skill is not discovered immediately.

## Usage

Invoke a skill explicitly with:

```text
Use $fowler-refactoring to improve a module or run a systematic code-hygiene campaign without changing observable behavior.

Use $paradigm-forge to design an original AI project direction with a concrete discovery loop.

Use $pushing-research-frontier to design a research plan for surpassing the strongest current baseline.
```

## Adding Skills

1. Create a directory under `skills/`.
2. Add a valid `SKILL.md` with `name` and `description` frontmatter.
3. Include only the references, scripts, and assets required by the skill.
4. Validate the skill before installing or sharing it.
5. Review bundled files for sensitive or project-specific information.
