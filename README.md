# skill issue.

Your agent has a skill issue.

Good thing skills are installable.

Reusable skills for AI-agent research workflows, engineering practices, personal automation, and focused learning.

The six skills use the open [Agent Skills format](https://agentskills.io/specification): one shared package per skill, with agent-neutral instructions and optional Codex metadata. Installation is documented for Codex, Claude Code, Gemini CLI, GitHub Copilot, Cursor, Windsurf/Cascade, OpenCode, and Kiro. Other agents supporting this format can use the same packages through their own discovery paths. See [agent compatibility](docs/agent-compatibility.md) for paths, invocation, and runtime limits.

## Available Skills

| Skill | Purpose |
| --- | --- |
| [`fowler-refactoring`](skills/fowler-refactoring/) | Refactor or systematically clean existing code through small verified transformations, evidence-backed dispositions, and proportionate guardrails. |
| [`mobile-app-design`](skills/mobile-app-design/) | Design, implement, review, and polish Expo/React Native interfaces with distinct iOS and Android behavior, purposeful motion, and evidence-based verification. |
| [`paradigm-forge`](skills/paradigm-forge/) | Design ambitious, original AI project directions with concrete discovery mechanisms and human judgment. |
| [`pushing-research-frontier`](skills/pushing-research-frontier/) | Plan, execute, and evaluate research intended to surpass the strongest current method. |
| [`research-to-runnable`](skills/research-to-runnable/) | Turn a computational problem, paper, or method repository into one runnable pilot with a credible comparison, reproducible evidence, and a practical decision. |
| [`top1percent`](skills/top1percent/) | Learn a topic or practical skill in about ten minutes through source-checked explanations, at least one illustration, examples, a short exercise, and a path toward mastery. |

## Structure

Each skill is a self-contained package:

```text
skills/
└── skill-name/
    ├── SKILL.md              # Shared instructions and standard frontmatter
    ├── agents/
    │   └── openai.yaml       # Optional Codex integration
    └── references/           # Supporting guidance, when needed
```

Skills may also include `scripts/` or `assets/` when needed. Install the complete skill directory, including references and bundled licenses.

`agents/openai.yaml` provides Codex presentation and invocation metadata; it is not the skill implementation or a requirement for other agents. The current files only configure display text and a default prompt. [OpenAI metadata documentation](https://learn.chatgpt.com/docs/build-skills#optional-metadata).

## Install

With Node.js/npm available, run the open [Skills CLI](https://github.com/vercel-labs/skills) from the project where you want to use the skills. First list the available packages:

```bash
npx skills add noestradamus/skills --list
```

Install one skill for selected agents, or all six:

```bash
npx skills add noestradamus/skills --skill mobile-app-design --agent claude-code codex --copy

npx skills add noestradamus/skills --skill '*' --agent codex claude-code gemini-cli github-copilot cursor windsurf opencode kiro-cli --copy
```

Keep only the agents you use. These commands install into the current project; add `--global` for personal installation. `--copy` avoids symlink requirements. The CLI is an optional third-party installer, not a runtime dependency of these skills. For installation without npm, use the [manual instructions and official agent paths](docs/agent-compatibility.md).

Package discovery and project installation were checked with Skills CLI **1.5.25**. See [the audit and verification record](docs/portability-verification.md) for the exact scope; installing files does not establish successful task execution in every agent.

## Usage

Ask for the skill by name in ordinary language, or select it through your agent's skill picker. Shortcut syntax varies by host; see [invocation details](docs/agent-compatibility.md).

```text
Use the fowler-refactoring skill to improve a module or run a systematic code-hygiene campaign without changing observable behavior.

Use the mobile-app-design skill to design and implement an Expo/React Native experience for iOS and Android.

Use the paradigm-forge skill to design an original AI project direction with a concrete discovery loop.

Use the pushing-research-frontier skill to design a research plan for surpassing the strongest current baseline.

Use the research-to-runnable skill to choose or adapt a method for this computational problem, run one useful pilot in my project, and explain what the evidence supports.

Use the top1percent skill to teach me evolution and natural selection in about ten minutes, starting from zero knowledge, including at least one illustration that explains a central idea, and ending with a path toward mastery.
```

## Adding Skills

1. Create a directory under `skills/`.
2. Add a valid `SKILL.md` with `name` and `description` frontmatter.
3. Include only the references, scripts, and assets required by the skill.
4. Follow the [portability checklist](docs/agent-compatibility.md#keeping-skills-portable) and validate the skill before sharing it.
5. Review bundled files for sensitive or project-specific information.
