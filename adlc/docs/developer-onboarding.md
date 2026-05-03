# ADLC Developer Onboarding

Setup guidance for developers using the Agentforce ADLC overlay.

Goal: every developer should have the same known-good local state before running ticket-driven ADLC work.

---

## Required State

A ready workstation has:

- Git access to the default repo (this repo). Remotes for canonical + mirror configurable via `tools/bootstrap_it_adlc.py --configure-remotes`.
- Salesforce CLI on `PATH`.
- Required Salesforce CLI command surfaces available:
  - `sf agent`
  - `sf project`
  - `sf data`
  - `sf apex`
  - `sf api`
  - `sf org`
- Authenticated Salesforce org aliases needed for the work.
- All 6 skills installed at `~/.cursor/skills/`, sourced from this repo's `adlc/skills/`:
  - **Custom (committed):** `adlc-drive`, `adlc-execute`, `adlc-ticket`.
  - **Vendored upstream (gitignored content, fetched by bootstrap):** `developing-agentforce`, `testing-agentforce`, `observing-agentforce`. Live in `adlc/skills/upstream/`.
- Cursor or Claude skill target directory available (`~/.cursor/skills/`).
- Local setup/status report captured for troubleshooting (optional, written to `adlc/versioning/`).

ADLC artifacts (HITL logs, ticket evidence) live under `adlc/agents/<agent>__<org>/tickets/`.

Current local reference captured during overlay/bootstrap setup:

```text
@salesforce/cli 2.130.9
agent 1.32.16
api 1.3.14
apex 3.9.17
data 4.0.85
deploy-retrieve 3.24.23
org 5.9.79
```

The exact minimum Salesforce CLI/plugin policy is still pending approval. Until then, setup/status should verify command availability, not only that `sf` exists.

---

## Install Order

Single source for skills (`adlc/skills/`), single bootstrap command. Bootstrap auto-vendors upstream skills on first install.

Required order:

1. **Salesforce prerequisites** — Install Salesforce CLI, verify required command surfaces, and authenticate required org aliases.
2. **Bootstrap** — Clone this repo and run `tools/bootstrap_it_adlc.py --install-additive`. This auto-vendors upstream Salesforce skills into `adlc/skills/upstream/` (cloning a cache at `~/agentforce-adlc-salesforce/` if needed), then installs all 6 skills (3 custom + 3 upstream) into `~/.cursor/skills/`.

The default repo contains: custom skill source (committed), upstream skill scaffolding (vendored content gitignored), docs, playbooks, bootstrap/status helpers, ticket guides, artifact conventions, and an empty Agentforce-focused SFDX scaffold (`force-app/`).

---

## Recommended Command Flow

Target flow for a clean machine:

```text
# 1. Install and verify Salesforce prerequisites first
node --version
npm --version
npm install --global @salesforce/cli
sf --version
sf agent --help
sf project --help
sf data --help
sf apex --help
sf api --help
sf org --help
sf org list

# 2. Clone this repo
git clone <your-default-repo-url> agentforce-project
cd agentforce-project

# 3. Dry-run: see what's installed and what's missing
python3 tools/bootstrap_it_adlc.py --status

# 4. Install: auto-vendors upstream skills + copies all 6 skills into ~/.cursor/skills/
python3 tools/bootstrap_it_adlc.py --install-additive

# 5. (Optional) Configure git remotes interactively
python3 tools/bootstrap_it_adlc.py --configure-remotes

# 6. Verify final machine state
python3 tools/bootstrap_it_adlc.py --status
```

To bump pinned upstream skill versions later:

```text
python3 tools/bootstrap_it_adlc.py --update-upstream-skills  # git pull cache + re-vendor
python3 tools/bootstrap_it_adlc.py --install-additive        # re-install (skips existing in ~/.cursor/skills/)
```

The bootstrap helper exists at `tools/bootstrap_it_adlc.py`. It currently targets Cursor skills only; there is no `--target` flag. Running it with no mode flag is equivalent to a dry run.

Current local status helper:

```text
python3 tools/bootstrap_it_adlc.py --dry-run
python3 tools/bootstrap_it_adlc.py --status
python3 tools/bootstrap_it_adlc.py --status --json
python3 tools/bootstrap_it_adlc.py --dry-run --write-report adlc/versioning/bootstrap-status-YYYY-MM-DD.json
python3 tools/bootstrap_it_adlc.py --install-additive --write-report adlc/versioning/bootstrap-install-YYYY-MM-DD.json
python3 tools/bootstrap_it_adlc.py --update-upstream-skills
python3 tools/bootstrap_it_adlc.py --configure-remotes
python3 tools/bootstrap_it_adlc.py --configure-remotes --canonical-url <URL> --mirror-url <URL>
```

This helper is intentionally conservative. Dry-run/status do not change files. `--install-additive` copies missing skills (custom + vendored upstream) and refuses to overwrite existing destination folders; it does not delete legacy `adlc-*` skills. `--update-upstream-skills` does replace existing vendored copies in `adlc/skills/upstream/<skill>/` (that's the point of bumping a pin), but never touches `~/.cursor/skills/`. `--configure-remotes` will not overwrite an existing remote — it reports it instead.

---

## Manual Status Checks

Minimum checks:

```text
sf --version
sf agent --help
sf project --help
sf data --help
sf apex --help
sf api --help
sf org --help
```

Repo checks:

```text
git remote -v
git branch --show-current
```

Skill checks (3 custom + 3 upstream):

```text
~/.cursor/skills/adlc-drive/SKILL.md
~/.cursor/skills/adlc-execute/SKILL.md
~/.cursor/skills/adlc-ticket/SKILL.md
~/.cursor/skills/developing-agentforce/SKILL.md
~/.cursor/skills/testing-agentforce/SKILL.md
~/.cursor/skills/observing-agentforce/SKILL.md
```

Custom skills source-of-truth (vendored in this repo):

```text
adlc/skills/adlc-drive/SKILL.md
adlc/skills/adlc-execute/SKILL.md
adlc/skills/adlc-ticket/SKILL.md
```

Project overlay checks:

```text
adlc/playbooks/agentforce-architecture-playbook.md
adlc/playbooks/prompt-engineering-playbook.md
adlc/playbooks/eval-report-playbook.md
adlc/docs/core-process-overlay.md
adlc/docs/acceptance-eval-hitl-governance.md
```

---

## Bootstrap Safety Rules

- Default mode must be non-destructive.
- Existing skill files in `~/.cursor/skills/` must not be overwritten unless the user explicitly invokes a reset mode.
- Existing local ticket artifacts must never be deleted by onboarding.
- Install Salesforce prerequisites first, then run a single bootstrap command for everything else.
- Vendored upstream skill content under `adlc/skills/upstream/` is gitignored (only `README.md` and `.gitkeep` are committed). Bootstrap auto-fetches from `~/agentforce-adlc-salesforce/` cache and rewrites `SOURCE.md` with the pinned commit on every fetch.
- Record upstream pinned commit + fetch timestamp in `adlc/skills/upstream/SOURCE.md`.
- Report skipped steps, conflicts, and version mismatches.

---

## Setup Report Contract

The status command produces a report with:

```json
{
  "timestamp": "YYYY-MM-DDTHH:MM:SSZ",
  "target": "cursor",
  "salesforce_cli": {
    "version": "<sf --version>",
    "commands_available": ["agent", "project", "data", "apex", "api", "org"]
  },
  "salesforce_upstream": {
    "repo": "https://github.com/SalesforceAIResearch/agentforce-adlc",
    "cache_clone": "/Users/<user>/agentforce-adlc-salesforce",
    "cache_present": true,
    "cache_remote": "https://github.com/SalesforceAIResearch/agentforce-adlc.git",
    "cache_commit": "<observed-commit>",
    "cache_skills_available": {
      "developing-agentforce": true,
      "testing-agentforce": true,
      "observing-agentforce": true
    },
    "vendored_dir": "/path/to/agentforce-project/adlc/skills/upstream",
    "vendored_skills_available": {
      "developing-agentforce": true,
      "testing-agentforce": true,
      "observing-agentforce": true
    }
  },
  "cursor_install": {
    "skills_dir": "/Users/<user>/.cursor/skills",
    "consolidated_skills": {},
    "local_custom_skills": {},
    "local_custom_skills_source": "/path/to/agentforce-project/adlc/skills",
    "custom_skills_available_in_repo": {},
    "legacy_standard_skills": {}
  },
  "local_overlay": {
    "docs": {},
    "current_workspace_remote": "<detected-origin-or-null>"
  },
  "planned_actions": [],
  "warnings": [],
  "blockers": [],
  "status": "ready|not-ready"
}
```

Do not declare `ready` if Salesforce CLI command surfaces or local overlay docs are missing.
