# Phase 3 Reference Check

## Scope

Checked Phase 3 local wrapper and documentation changes:

- `~/.cursor/skills/adlc-drive/SKILL.md`
- `~/.cursor/skills/adlc-execute/SKILL.md`
- `README.md`
- `adlc/docs/core-process-overlay.md`
- `adlc/docs/artifact-repo-workflow.md`
- `adlc/docs/developer-onboarding.md`
- `adlc/docs/PROJECT-MAP.md`
- `adlc/docs/PROJECT-MAP.html`
- `adlc/docs/drive-architecture.md`
- `tools/bootstrap_it_adlc.py`
- `adlc/ticket-guides/ticket-authoring-prompt.md`
- `adlc/ticket-guides/ticket-template.md`
- `adlc/versioning/PLAN_EXECUTION_STATUS.md`

No Salesforce upstream standard skill content was modified.

## Checks

| Check | Status | Notes |
|---|---|---|
| `adlc-drive` reads local overlay docs | Pass | Skill now points to architecture, core overlay, and governance docs before execution. |
| `adlc-drive` requires Discover dependency map | Pass | Phase 3 now requires dependency map and testability classifications before test construction. |
| `adlc-execute` reads local overlay docs | Pass | Skill now reads architecture, core overlay, and governance docs before planning. |
| Solution Strategy Review wired into execution | Pass | `adlc-execute` Phase 4 now includes a required Solution Strategy Review before triage and plan options. |
| Acceptance governance wired into presentation | Pass | `adlc-execute` Phase 6 now reads acceptance/eval/HITL governance and includes product, technical/process, and testability sections. |
| Artifact repo guardrail wired into handoff | Pass | `adlc-execute` Phase 7 now verifies artifact package and routes to `https://github.com/YOUR_ORG/YOUR_ADLC_ARTIFACT_REPO`. |
| Artifact workflow doc created | Pass | `adlc/docs/artifact-repo-workflow.md` defines repo routing, layout, closeout package, and rollups. |
| Developer onboarding doc created | Pass | `adlc/docs/developer-onboarding.md` defines setup/status expectations, bootstrap helper commands, and Salesforce CLI command surface checks. |
| Legacy docs refreshed | Pass | README, project map, drive architecture, and key ticket guides now point to current overlay docs, wrapper phase ownership, bootstrap helper behavior, and artifact repo rules. |
| Old upstream reference scan | Pass with historical caveat | `almandsky/agentforce-adlc` remains only in historical versioning audit reports. Live docs were updated. |
| Salesforce CLI command surfaces | Pass | `sf --version` returned `@salesforce/cli/2.130.9`; `sf agent`, `sf project`, `sf data`, `sf apex`, `sf api`, and `sf org` help commands succeeded. CLI reports update available to `2.131.7`. |
| Linter diagnostics | Pass | `ReadLints` returned no linter errors for changed skills/docs. |

## Known Remaining Work

- Corporate artifact repo `https://github.com/YOUR_ORG/YOUR_ADLC_ARTIFACT_REPO` is not cloned in this workspace, so actual push/PR workflow was documented but not verified against the remote.
- Bootstrap helper exists at `tools/bootstrap_it_adlc.py` and has been run for dry-run/status and additive consolidated skill install evidence.
- Salesforce CLI minimum/version policy remains pending approval; current local version is documented as a reference, not a final company minimum.
