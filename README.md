# Agentforce ADLC Default Repo

This workspace is the **default repo** for Agentforce ADLC work: custom skills, local process docs, playbooks, bootstrap/status tooling, ticket guides, artifact conventions, and an empty Agentforce-focused SFDX scaffold.

All skills are installed from one source — `adlc/skills/` — by the bootstrap script:

- **Custom skills** (`adlc-drive`, `adlc-execute`, `adlc-ticket`) are committed to `adlc/skills/`.
- **Upstream Salesforce skills** (`developing-agentforce`, `testing-agentforce`, `observing-agentforce`) are vendored into `adlc/skills/upstream/` by the bootstrap script. The skill content itself is gitignored — only `README.md` and `.gitkeep` are committed there.

Bootstrap auto-fetches and vendors upstream skills on first install. Run `--update-upstream-skills` later to bump the pinned upstream versions.

> **First time here?** Read `adlc/docs/developer-onboarding.md` for the complete setup walkthrough. The short version is in **Useful Commands** below.

## Install Order

Single install command. Bootstrap handles everything additively:

1. **Salesforce prerequisites** — Salesforce CLI, required `sf` command surfaces, and org auth.
2. **One bootstrap command** — `python3 tools/bootstrap_it_adlc.py --install-additive`. This:
   - Auto-vendors upstream Salesforce skills into `adlc/skills/upstream/` (clones/pulls a cache at `~/agentforce-adlc-salesforce/` if needed).
   - Copies all 6 skills (3 custom + 3 upstream) from `adlc/skills/` into `~/.cursor/skills/`.
   - Skips skills already installed (additive only — never overwrites or deletes).

See `adlc/docs/developer-onboarding.md` for the full setup flow.

## Start Here

- `adlc/docs/developer-onboarding.md`
- `adlc/docs/drive-architecture.md`
- `adlc/docs/core-process-overlay.md`
- `adlc/docs/acceptance-eval-hitl-governance.md`
- `adlc/playbooks/eval-report-playbook.md`

## Useful Commands

Install Salesforce CLI if needed:

```text
node --version
npm --version
npm install --global @salesforce/cli
sf --version
```

Install everything (run from your clone of this repo):

```text
python3 tools/bootstrap_it_adlc.py --status            # see what's installed
python3 tools/bootstrap_it_adlc.py --install-additive  # install missing skills (auto-vendors upstream)
python3 tools/bootstrap_it_adlc.py --configure-remotes # set up git remotes (first clone only)
```

`--install-additive` is the one-command install. It auto-vendors upstream Salesforce skills into `adlc/skills/upstream/` (cloning the cache if needed) before copying everything to `~/.cursor/skills/`.

To bump upstream skill versions later:

```text
python3 tools/bootstrap_it_adlc.py --update-upstream-skills  # git pull cache + re-vendor
python3 tools/bootstrap_it_adlc.py --install-additive        # re-install (skips existing in ~/.cursor/skills/)
```

The bootstrap helper is conservative. It never overwrites or deletes existing skills in `~/.cursor/skills/`. To force-update an installed skill, delete its directory first.

`--configure-remotes` prompts interactively for canonical + mirror git URLs and runs `git init` if needed. Use this on first clone instead of hardcoding remote URLs in the repo.

## Repository Boundaries

- Keep custom skills, overlay docs, ticket guides, and artifact conventions here.
- `force-app/` ships as an **empty Agentforce-focused SFDX scaffold** — buckets for `aiAuthoringBundles/`, `aiEvaluationDefinitions/`, `bots/`, `genAiPlannerBundles/`, `genAiPromptTemplates/`, `classes/`, and `flows/`. See `force-app/README.md`.
- Production agent metadata (specific `.agent` bundles, bots, planner bundles, eval XMLs for real agents) lives in your team's **production agent repo**, not here.
- Per-ticket ADLC artifacts (HITL logs, discovery JSON, eval reports) live under `adlc/agents/<agent>__<org>/tickets/<ticket>/`.
- Keep generated local install evidence such as `adlc/versioning/bootstrap-*.json` out of commits (already gitignored).
- Vendored upstream Salesforce skills under `adlc/skills/upstream/` are gitignored except for `README.md` and `.gitkeep`. The folder structure is committed; the skill content is runtime-fetched. Cache lives at `~/agentforce-adlc-salesforce/`.
