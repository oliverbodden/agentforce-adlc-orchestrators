# ADLC Developer Onboarding

Setup guidance for developers using the Agentforce ADLC overlay.

Goal: every developer should have the same known-good local state before running ticket-driven ADLC work.

---

## Required State

A ready workstation has:

- Git access to the shared ADLC artifact repo.
- Salesforce CLI on `PATH`.
- Required Salesforce CLI command surfaces available:
  - `sf agent`
  - `sf project`
  - `sf data`
  - `sf apex`
  - `sf api`
  - `sf org`
- Authenticated Salesforce org aliases needed for the work.
- Salesforce upstream ADLC skills installed at the approved baseline.
- Project/local overlay installed additively.
- Cursor or Claude skill target directory available.
- Artifact repo remote pointing to `https://github.com/YOUR_ORG/YOUR_ADLC_ARTIFACT_REPO`.
- Local setup/status report captured for troubleshooting.

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

Install order matters. The local overlay assumes Salesforce prerequisites and Salesforce upstream skills already exist. Do not install or update local wrapper skills first and then backfill Salesforce skills around them.

Required order:

1. **Salesforce prerequisites** — Install Salesforce CLI, verify required command surfaces, and authenticate required org aliases.
2. **Salesforce upstream ADLC baseline** — Install or verify the standard consolidated Salesforce skills from `https://github.com/SalesforceAIResearch/agentforce-adlc`.
3. **Project/local ADLC overlay** — Install or verify local wrapper skills, overlay docs, playbooks, bootstrap/status tooling, and artifact repo routing from `https://github.com/YOUR_ORG/YOUR_ADLC_ARTIFACT_REPO`.

The artifact repo should contain local overlay source, docs, playbooks, bootstrap/status helpers, and artifact conventions. It should not vendor copied Salesforce upstream skill directories.

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

# 2. Install or verify Salesforce upstream ADLC baseline
git clone https://github.com/SalesforceAIResearch/agentforce-adlc.git ~/agentforce-adlc-salesforce
cd ~/agentforce-adlc-salesforce
python3 tools/install.py --target cursor
# Alternative one-command upstream install:
# curl -sSL https://raw.githubusercontent.com/SalesforceAIResearch/agentforce-adlc/main/tools/install.sh | bash
# Required installed skills: developing-agentforce, testing-agentforce, observing-agentforce.

# 3. Clone the Project/local overlay repo
git clone https://github.com/YOUR_ORG/YOUR_ADLC_ARTIFACT_REPO.git
cd YOUR_ADLC_ARTIFACT_REPO

# 4. Dry-run: show what local overlay/bootstrap would install or verify
python3 tools/bootstrap_it_adlc.py --dry-run

# 5. Add missing consolidated Salesforce skills only if upstream is present locally
python3 tools/bootstrap_it_adlc.py --install-additive

# 6. Verify final machine state
python3 tools/bootstrap_it_adlc.py --status
```

The bootstrap helper exists at `tools/bootstrap_it_adlc.py`. It currently targets Cursor skills only; there is no `--target` flag. Running it with no mode flag is equivalent to a dry run. The helper is additive: it must not overwrite local wrapper skills, delete legacy skills, or vendor Salesforce upstream skill content into the artifact repo.

Current local status helper:

```text
python3 tools/bootstrap_it_adlc.py --dry-run
python3 tools/bootstrap_it_adlc.py --status
python3 tools/bootstrap_it_adlc.py --status --json
python3 tools/bootstrap_it_adlc.py --dry-run --write-report adlc/versioning/bootstrap-status-YYYY-MM-DD.json
python3 tools/bootstrap_it_adlc.py --install-additive --write-report adlc/versioning/bootstrap-install-YYYY-MM-DD.json
```

This helper is intentionally conservative. Dry-run/status do not change files. `--install-additive` only copies missing consolidated Salesforce skills and refuses to overwrite existing destination folders; it does not delete legacy `adlc-*` skills.

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

Skill checks:

```text
~/.cursor/skills/adlc-drive/SKILL.md
~/.cursor/skills/adlc-execute/SKILL.md
~/.cursor/skills/adlc-ticket/SKILL.md
~/.cursor/skills/developing-agentforce/SKILL.md
~/.cursor/skills/testing-agentforce/SKILL.md
~/.cursor/skills/observing-agentforce/SKILL.md
```

Project overlay checks:

```text
adlc/playbooks/agentforce-architecture-playbook.md
adlc/docs/core-process-overlay.md
adlc/docs/acceptance-eval-hitl-governance.md
adlc/docs/artifact-repo-workflow.md
```

---

## Bootstrap Safety Rules

- Default mode must be non-destructive.
- Existing standard Salesforce skill files must not be overwritten unless the user explicitly invokes a reset mode.
- Existing local ticket artifacts must never be deleted by onboarding.
- Install Salesforce prerequisites first, Salesforce standard skills second, and Project/local overlays third.
- Keep Salesforce upstream skill directories out of the local overlay repo; install them into the user's skill directory from the Salesforce upstream source.
- Record upstream commit/version and local overlay version.
- Report skipped steps, conflicts, and version mismatches.
- If the current working repo is a production agent repo, do not place shared HITL artifacts there.

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
    "local_clone": "/Users/<user>/agentforce-adlc-salesforce",
    "remote": "https://github.com/SalesforceAIResearch/agentforce-adlc.git",
    "commit": "<observed-commit>",
    "skills_available": {
      "developing-agentforce": true,
      "testing-agentforce": true,
      "observing-agentforce": true
    }
  },
  "cursor_install": {
    "skills_dir": "/Users/<user>/.cursor/skills",
    "consolidated_skills": {},
    "local_wrappers": {},
    "legacy_standard_skills": {}
  },
  "local_overlay": {
    "docs": {},
    "artifact_repo": "https://github.com/YOUR_ORG/YOUR_ADLC_ARTIFACT_REPO",
    "current_workspace_remote": "<detected-origin-or-null>"
  },
  "planned_actions": [],
  "warnings": [],
  "blockers": [],
  "status": "ready|not-ready"
}
```

Do not declare `ready` if Salesforce CLI command surfaces, local overlay docs, or artifact repo routing are missing.
