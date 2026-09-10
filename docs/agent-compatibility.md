# Agent compatibility

Official documentation checked **2026-09-10**. These agents support native `SKILL.md` packages. This establishes format and discovery support; it does not mean this collection has been run successfully in every client. See the [verification record](portability-verification.md) for checks actually performed.

The packages under `skills/` are the shared source. Install the **complete skill folder**, including its references, scripts, assets, and licenses. Keep each `<skill-name>/SKILL.md` one directory below the chosen skill root.

## Discovery and invocation

Project roots belong inside the repository where you want to use a skill. Personal roots apply across local projects; `~` means your home directory. Choose one supported root for each installation, avoiding duplicate copies of the same skill in multiple discovery roots.

| Agent | Project skill root | Personal skill root | Explicit use |
| --- | --- | --- | --- |
| [Codex](https://learn.chatgpt.com/docs/build-skills) | `.agents/skills/` | `~/.agents/skills/` | CLI/IDE: `$skill-name` or `/skills`; desktop: skill picker |
| [Claude Code](https://code.claude.com/docs/en/skills) | `.claude/skills/` | `~/.claude/skills/` | `/skill-name` |
| [Gemini CLI](https://geminicli.com/docs/cli/using-agent-skills/) | `.gemini/skills/` or `.agents/skills/` | `~/.gemini/skills/` or `~/.agents/skills/` | Ask to use the skill; `/skills list` checks discovery |
| [GitHub Copilot](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills) | `.github/skills/`, `.claude/skills/`, or `.agents/skills/` | `~/.copilot/skills/` or `~/.agents/skills/` | Ask to use the skill by name |
| [Cursor](https://cursor.com/docs/skills) | `.cursor/skills/` or `.agents/skills/` | `~/.cursor/skills/` or `~/.agents/skills/` | `/` picker, then the skill name |
| [Windsurf / Cascade](https://docs.devin.ai/desktop/cascade/skills) | `.windsurf/skills/` or `.agents/skills/` | `~/.codeium/windsurf/skills/` or `~/.agents/skills/` | `@skill-name` |
| [OpenCode](https://opencode.ai/docs/skills/) | `.opencode/skills/`, `.claude/skills/`, or `.agents/skills/` | `~/.config/opencode/skills/`, `~/.claude/skills/`, or `~/.agents/skills/` | Ask to use the skill by name |
| [Kiro](https://kiro.dev/docs/skills/) | `.kiro/skills/` | `~/.kiro/skills/` | `/skill-name` |

All eight can select relevant skills automatically. Host permissions, trust settings, and custom-agent configuration still apply: Gemini workspace skills require a [trusted workspace](https://geminicli.com/docs/cli/tutorials/skills-getting-started/); Kiro custom agents need [skill resource entries](https://kiro.dev/docs/cli/skills/). Windsurf's official skills documentation now redirects to Devin Desktop/Cascade and retains the paths shown above.

Personal files do not automatically follow you into cloud sessions. Claude Code cloud sessions can use committed project skills; Cursor offers explicit sync for `~/.cursor/skills/`, while `~/.agents/skills/` remains local. Kiro personal skills are for IDE/CLI. Use the linked host documentation for remote setup.

The table describes current host discovery paths. Installer versions can select a different supported path, especially for personal installations. The [README installer example](../README.md#install) uses project scope; check the destination it reports instead of assuming it matches every personal path above.

## Manual installation

From the root of this cloned repository, these examples install **one skill for your personal Claude Code setup**. Change the skill name and root to another entry above as needed. For project scope, set the root to the target project's full path plus its chosen skill directory. Both examples stop if that skill's destination already exists; review an existing installation before updating it.

macOS/Linux, Bash:

```bash
(
  set -eu
  skill_name=mobile-app-design
  skill_root="$HOME/.claude/skills"
  skill_destination="$skill_root/$skill_name"
  test -f "skills/$skill_name/SKILL.md"
  mkdir -p "$skill_root"
  mkdir "$skill_destination" # Intentionally fails if the destination exists.
  cp -R "skills/$skill_name/." "$skill_destination/"
)
```

Windows, PowerShell:

```powershell
$skillName = 'mobile-app-design'
$skillSource = Join-Path (Get-Location) "skills/$skillName"
$skillRoot = Join-Path ([Environment]::GetFolderPath('UserProfile')) '.claude/skills'
$skillDestination = Join-Path $skillRoot $skillName
if (-not (Test-Path -LiteralPath (Join-Path $skillSource 'SKILL.md') -PathType Leaf)) {
    throw 'Run this from the repository root and choose an existing skill.'
}
[System.IO.Directory]::CreateDirectory($skillRoot) | Out-Null
if (Test-Path -LiteralPath $skillDestination) {
    throw "Destination already exists: $skillDestination"
}
New-Item -ItemType Directory -Path $skillDestination -ErrorAction Stop | Out-Null
Get-ChildItem -LiteralPath $skillSource -Force |
    Copy-Item -Destination $skillDestination -Recurse -ErrorAction Stop
```

Refresh the host's skill list or start a new session, then ask: “Use the mobile-app-design skill to review this screen.” Seeing a file on disk is only an installation check; confirm the host discovers it and reads the relevant references.

If an agent has no native skill loader, provide the complete `SKILL.md` as task guidance and make its referenced files available, preserving their paths relative to the skill folder. Ask the agent to read those references when directed. This is manual use of the guidance, not native skill discovery; it does not add missing tools or permissions.

## Keeping skills portable

- Maintain one shared package per skill, with standard `name` and `description` frontmatter and relative resource paths. Match the skill's name to its folder.
- Keep host-specific shortcuts and UI metadata optional. `agents/openai.yaml` enhances OpenAI integration; shared instructions must remain usable without it.
- Describe required capabilities and dependencies explicitly. When a capability is unavailable, state the resulting limit and follow any fallback defined by the skill; do not silently lower its quality requirements.
- Avoid requiring proprietary tool names, model identifiers, absolute machine paths, or host-specific interpolation in shared instructions. An optional adapter must not carry essential workflow behavior.
- Preserve progressive loading: a focused `SKILL.md` routes to supporting references as needed. Copy and distribute the entire package.
- Validate structure, verify installation, and test representative tasks separately. Record the agent/version and observed result before claiming runtime compatibility.

Use the [Agent Skills specification](https://agentskills.io/specification) and its linked reference validator. After installing `skills-ref` according to its official instructions, run this from the repository root:

```bash
for skill_dir in skills/*; do
  skills-ref validate "$skill_dir" || exit 1
done
```

This validates frontmatter and naming. It does not test task quality, tool availability, or client-specific execution.
