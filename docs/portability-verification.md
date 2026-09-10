# Portability audit and verification

Checked **2026-09-10** against the six packages from repository commit `a59bc8724a61b3d9db4656eecd4e287fcdf96e27`. This change preserves their contents and updates repository documentation.

## What is portable

All six packages use standard `name` and `description` frontmatter. Their instructions and relative references are agent-neutral. The audit covered all 22 Markdown files and six `agents/openai.yaml` files under `skills/`.

There are no bundled executable scripts, hard-coded personal filesystem paths, proprietary tool calls, or mandatory Codex integrations to port. The six `agents/openai.yaml` files only supply optional Codex display text and default prompts. `research-to-runnable` mentions `pushing-research-frontier` conditionally; it does not require another skill for ordinary adoption work.

The previous barriers were Codex-only installation instructions, `$skill-name` presented as universal invocation syntax, and an unexplained `openai.yaml` file. Rewriting the skill workflows would not solve those barriers. They now share agent-neutral usage examples and documented installation routes.

## Capabilities still matter

A compatible skill loader supplies instructions. The host must separately provide the capabilities needed for the requested work; the skill does not install tools or grant permissions.

| Skill | Capabilities needed for the requested endpoint | Evidence boundary when unavailable |
| --- | --- | --- |
| `fowler-refactoring` | Project-file access and editing; the project's relevant verification commands for implementation. | An audit or proposed change is not a verified refactor. Report unavailable checks and follow the skill's verification limits. |
| `mobile-app-design` | Project access for implementation; rendering and interaction tools for visual QA; native runtime/device access for native verification. | Design and code review remain useful. A web preview cannot verify native behavior; code inspection cannot prove device performance. |
| `paradigm-forge` | Supplied context for ideation; current sources for claims of originality. | Without a literature/current-work check, novelty remains unverified. |
| `pushing-research-frontier` | Fresh source evidence and appropriate data, compute, execution, and measurement for empirical claims. | Planning is possible without execution. A frontier win requires the specified comparative evidence. |
| `research-to-runnable` | Source/project/data access and the project's runtime for an executed pilot. | Planning-only requests remain planning-only. Blocked execution is partial completion, not a measured pilot. |
| `top1percent` | Sources for factual checks and a way to display at least one meaningful illustration. | A simpler rendered static graphic can replace interactivity. A lesson with no displayed illustration is incomplete unless the user explicitly requests text only. |

These are existing task requirements, not new dependencies. Different agents, models, enabled tools, permissions, and local/cloud environments can produce different outcomes.

## Checks performed

| Check | Result | What it establishes |
| --- | --- | --- |
| Official agent documentation | Native `SKILL.md` support documented for all eight listed agents; links and paths in [agent compatibility](agent-compatibility.md). | Documented format support, not client execution. |
| Agent Skills reference validator | All six packages passed `skills-ref validate`. | Frontmatter and naming conformance. |
| Remote installer discovery | `npx skills@1.5.25 add noestradamus/skills --list` found all six. | Repository layout is discoverable by that installer version. |
| Temporary project installation | All six installed with `--copy` for eight agent targets. | Installer routing and package copying work. |
| Complete-file comparisons | All 24 installed package trees matched source filenames and SHA-256 contents. | No missing or modified instructions, references, metadata, or licenses. |
| Manual Bash installation | Copied the 16-file mobile package intact; a second attempt refused the existing destination. | The documented copy procedure preserves package contents and existing installations. |
| Local documentation links | 98 file/heading links passed inspection. | Repository-relative references resolve. |

The installer uses four distinct project roots for these eight targets: `.agents/skills`, `.claude/skills`, `.windsurf/skills`, and `.kiro/skills`. Agents sharing `.agents/skills` do not need duplicate package copies there.

The validator came from [Agent Skills reference implementation](https://github.com/agentskills/agentskills/tree/69ef37e9424c0a7ea9dd2293b559e43ec8176379/skills-ref), revision `69ef37e9424c0a7ea9dd2293b559e43ec8176379`. It checks package format; its upstream README identifies it as a demonstration library, not a production runtime.

To repeat the installation check, run from an empty temporary project directory, replacing the path placeholder with an absolute path to this checkout:

```bash
npx skills@1.5.25 add /absolute/path/to/skills-repository --skill '*' --agent codex claude-code gemini-cli github-copilot cursor windsurf opencode kiro-cli --copy --yes
```

No agent clients were launched to execute these skills during this audit. Personal/global installations, cloud discovery, Windows execution, and equivalent output quality across models were not tested. Future runtime results should record the agent/version, skill revision, task, enabled capabilities, actual output, and observed limitations separately from these packaging checks.
