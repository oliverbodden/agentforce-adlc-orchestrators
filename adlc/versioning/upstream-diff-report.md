# Upstream Diff Report

## Summary

Phase 0 compared the latest Salesforce upstream ADLC repo against the currently installed Cursor skills, the legacy local orchestrator repo, and the current workspace ADLC docs.

## Sources

| Source | Location | Version / Commit | Notes |
|---|---|---|---|
| Salesforce upstream | `https://github.com/SalesforceAIResearch/agentforce-adlc` / `/Users/obguzman/agentforce-adlc-salesforce` | `0.1.0`, `4fa57e376d7b6f372ba4a765fce475df5924bbfa` | New standard baseline candidate |
| Legacy local orchestrator | `https://github.com/oliverbodden/agentforce-adlc-orchestrators.git` / `/Users/obguzman/agentforce-adlc-custom` | `8975c818a2ead7c488fed389019e6320f6cfae5c` | Custom orchestrators and legacy patches |
| Installed Cursor skills | `/Users/obguzman/.cursor/skills` | Not git tracked | Currently active local skill installation |
| Current workspace | `/Users/obguzman/agentforce-project` | Not a git repo | Contains ADLC docs/playbooks/artifacts |
| Corporate artifact repo | `https://github.com/YOUR_ORG/YOUR_ADLC_ARTIFACT_REPO` | Not cloned during this phase | Planned canonical artifact repo |

## Upstream Structure

Salesforce upstream now uses three consolidated skills:

| Upstream skill | Covers |
|---|---|
| `developing-agentforce` | Author, discover, scaffold, deploy, safety, feedback |
| `testing-agentforce` | Preview testing, Testing Center batch testing, action execution |
| `observing-agentforce` | STDM/session trace analysis, reproduce, optimize |

Upstream README lists old skill names as aliases:

| Legacy name | Upstream target |
|---|---|
| `adlc-author` | `developing-agentforce` |
| `adlc-discover` | `developing-agentforce` |
| `adlc-scaffold` | `developing-agentforce` |
| `adlc-deploy` | `developing-agentforce` |
| `adlc-safety` | `developing-agentforce` |
| `adlc-feedback` | `developing-agentforce` |
| `adlc-test` | `testing-agentforce` |
| `adlc-run` | `testing-agentforce` |
| `adlc-optimize` | `observing-agentforce` |

## Current Installed Skills

Installed Cursor skills still use the older individual skill layout:

- `adlc-author`
- `adlc-deploy`
- `adlc-discover`
- `adlc-drive`
- `adlc-execute`
- `adlc-feedback`
- `adlc-optimize`
- `adlc-run`
- `adlc-scaffold`
- `adlc-test`
- `adlc-ticket`

Additional non-ADLC skills are also installed, such as `agentforce-testing-analysis` and `generate-docs`.

## Legacy Local Repo

The legacy local repo tracks:

- Custom skills: `adlc-drive`, `adlc-execute`, `adlc-ticket`
- Legacy additive patches:
  - `adlc-discover-section0.md`
  - `adlc-optimize-section3ui.md`
  - `adlc-test-csv-export.md`
- Custom project framework:
  - `adlc/playbooks/prompt-engineering-playbook.md`
  - `adlc/docs/`
  - `adlc/ticket-guides/`
  - `adlc/scripts/generate_report.py`
  - `adlc/eval-config/`

The legacy repo README says it was built on top of the older `almandsky/agentforce-adlc` upstream. That upstream is no longer the correct baseline if `SalesforceAIResearch/agentforce-adlc` is approved as authoritative.

## Comparison Findings

### Upstream vs Installed Cursor Skills

The installed skills are not aligned with the latest Salesforce upstream structure. The comparison is not a simple file-level patch because upstream consolidated many old skills into three new skill directories.

High-level difference:

- Upstream has `developing-agentforce`, `testing-agentforce`, and `observing-agentforce`.
- Installed Cursor has older `adlc-*` skill directories.
- Some installed old skill assets overlap with upstream content, but paths and ownership changed.
- Installed custom `adlc-drive`, `adlc-execute`, and `adlc-ticket` do not exist in Salesforce upstream.

`git diff --no-index --stat` between upstream `skills/` and installed `~/.cursor/skills/` reported 110 changed paths, reflecting both the consolidated upstream model and the older installed layout.

### Upstream vs Legacy Local Repo

The legacy local repo is also not aligned with the latest Salesforce upstream structure.

High-level difference:

- Legacy local repo has custom orchestration skills and patch files.
- Salesforce upstream has consolidated skills plus extensive assets/references under the consolidated directories.
- Legacy local repo includes custom ADLC project framework files not present upstream.

`git diff --no-index --stat` between upstream `skills/` and legacy `skills/` reported 99 changed paths.

### Legacy Repo vs Current Workspace

Earlier Phase 0 checks showed the following current workspace files match the legacy repo exactly:

- `adlc/playbooks/prompt-engineering-playbook.md`
- `adlc/docs/`
- `adlc/ticket-guides/`
- `adlc/scripts/generate_report.py`

Known differences:

- Current workspace has extra archived scripts under `adlc/scripts/_archived/`.
- Current workspace does not have legacy `adlc/eval-config/`.
- Current workspace now has new Phase 0 versioning artifacts under `adlc/versioning/`.

### Legacy Repo vs Installed Cursor Skills

Core custom skill files match between legacy repo and installed skills:

- `adlc-drive/SKILL.md`
- `adlc-execute/SKILL.md`
- `adlc-ticket/SKILL.md`

Known difference:

- `adlc-drive/examples/phase-outputs.md` differs between the legacy repo and installed skills.

The installed skills also include many base `adlc-*` skills as full directories, while the legacy repo only tracks custom skills and patch files.

## Additive Patch Markers Found In Installed Skills

The currently installed skills contain legacy local patch markers:

| Installed skill | Marker |
|---|---|
| `adlc-discover` | `Agent/Topic Resolution (UI-built agents)` |
| `adlc-optimize` | `3.UI: Tooling API Path (UI-built agents)` |
| `adlc-test` | `Phase 3: Export and Analyze Results`, `contextVariables`, HTML unescape guidance |

These need remapping against the Salesforce consolidated skill model before any install/update work.

## Risks

- Directly patching old `adlc-*` skills would preserve drift from the new Salesforce standard.
- Replacing installed skills with upstream without overlay planning would lose local custom orchestration and project workflow.
- `adlc-optimize` contains local Tooling API guidance that may conflict semantically with newer upstream guidance preferring `.agent` files as source of truth. This requires explicit review.
- The corporate artifact repo is not cloned locally yet, so artifact submission workflow cannot be verified until that repo is inspected.
- Salesforce CLI is not optional for project developer execution even though the upstream installer treats it as optional. Skills rely on `sf agent`, `sf project`, `sf data`, `sf apex`, and `sf api` command surfaces.

## Salesforce CLI Local Check

Current local machine state:

```text
@salesforce/cli 2.130.9
agent 1.32.16 (core)
api 1.3.14 (core)
apex 3.9.17 (core)
data 4.0.85 (core)
deploy-retrieve 3.24.23 (core)
org 5.9.79 (core)
```

`sf agent --help`, `sf project --help`, and `sf api --help` are available locally. Onboarding/bootstrap should verify these command surfaces for every developer machine before declaring setup complete.

## Phase 0 Recommendation

Use the latest Salesforce upstream as the standard baseline, then layer local behavior as a separate project overlay:

1. Keep Salesforce consolidated skill content unmodified.
2. Preserve local `adlc-drive`, `adlc-execute`, and `adlc-ticket` behavior as wrapper/process overlays unless a better consolidated-skill extension point is identified.
3. Convert legacy patches into reviewed additive overlays or project playbook guidance.
4. Require a skill-regression/reference audit after mapping and again after docs/onboarding updates.
5. Present and approve target structure before implementation changes.
