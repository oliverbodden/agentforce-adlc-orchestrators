# Phase 1 Reference Check

## Scope

Checked Phase 1 local documentation changes:

- `adlc/playbooks/agentforce-architecture-playbook.md`
- `adlc/docs/core-process-overlay.md`
- `adlc/playbooks/prompt-engineering-playbook.md`
- `adlc/versioning/PLAN_EXECUTION_STATUS.md`

No Salesforce upstream standard skill content was modified.

## Checks

| Check | Status | Notes |
|---|---|---|
| Architecture playbook created | Pass | Includes official references, terminology, runtime model, architecture surfaces, failure taxonomy, Discover dependency map, and Solution Strategy Review. |
| Prompt playbook points to architecture reference | Pass | Top section now states prompt playbook is for instruction craft and architecture classification belongs in `adlc/playbooks/agentforce-architecture-playbook.md`. |
| Core overlay guidance created | Pass | Separates local project process controls from Salesforce standard skills. |
| Discover dependency map guidance present | Pass | Included in both architecture playbook and core process overlay. |
| Solution Strategy Review guidance present | Pass | Included in both architecture playbook and core process overlay. |
| Testing layers separated | Pass | `core-process-overlay.md` separates deterministic unit tests, ticket-goal validation, bulk regression evals, bulk feature evals, and scenario simulation. |
| Old skill references checked | Pass | Old `adlc-*` references appear only where describing local wrappers or known aliases/legacy concepts. |
| Salesforce consolidated skill references checked | Pass | `developing-agentforce`, `testing-agentforce`, and `observing-agentforce` referenced as upstream standard capabilities. |
| Linter diagnostics | Pass | `ReadLints` returned no linter errors for Phase 1 docs. |

## Known Remaining Work

- Legacy docs still require Phase 3 refresh:
  - `README.md`
  - `adlc/docs/PROJECT-MAP.md`
  - `adlc/docs/PROJECT-MAP.html`
  - `adlc/docs/drive-architecture.md`
  - `adlc/ticket-guides/*`
- Phase 2 must still add acceptance, eval report, HITL, and environment/testability governance.
- Phase 3 must still add onboarding/bootstrap and artifact repo operations.
