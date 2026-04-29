# adlc-drive — Architecture & Delegation Map

## Current Status

This map is a current orientation aid, not the authoritative skill text. Current ADLC behavior is governed by:

- `adlc/playbooks/agentforce-architecture-playbook.md`
- `adlc/docs/core-process-overlay.md`
- `adlc/docs/acceptance-eval-hitl-governance.md`
- `adlc/docs/artifact-repo-workflow.md`
- `adlc/docs/developer-onboarding.md`
- Local wrapper skills `adlc-drive` and `adlc-execute`

Salesforce upstream standard skills are treated as the baseline and must not be modified directly. Local behavior is layered through wrappers and overlay docs.

`adlc-drive` owns Phases 1-3 and must stop after the Phase 3 handoff checkpoint. `adlc-execute` owns Phases 4-7. The Salesforce skills are execution tools; they do not replace the wrapper phases.

## Step-by-Step Flow


| Phase           | Step                         | What happens                                              | Calls                                 |
| --------------- | ---------------------------- | --------------------------------------------------------- | ------------------------------------- |
| **1. Goal**     | 1a. Parse input              | Extract ticket key or free text                           | Drive directly                        |
|                 | 1b. Pull JIRA ticket         | Fetch title, description, AC                              | `user-atlassian` MCP → `getJiraIssue` |
|                 | 1c. Find agent/topic in org  | Resolve API names, instruction record IDs                 | `developing-agentforce`              |
|                 | 1d. Normalize goal           | Map JIRA fields to goal structure                         | Drive directly                        |
| **2. Refine**   | 2a. Scope                    | Discuss topics, actions, surfaces with user               | Drive directly                        |
|                 | 2b. SPIKE gate               | Uncertainty check                                         | Drive directly                        |
|                 | 2c. Confirm alignment        | Present summary, get approval                             | Drive directly                        |
| **3. Discover** | 3a. Resolve metadata/source  | Resolve agent/topic IDs, canonical folder, source of truth, and prior HITL context | `developing-agentforce` + Drive       |
|                 | 3b. Pull current state       | Save originals, audit conflicts, build prompt mental model and dependency map | `observing-agentforce` or UI-built exception path |
|                 | 3c. Baseline + test specs    | Build regression/capability specs from baseline utterances, ticket examples, and derived cases; run fresh baseline CSV | `testing-agentforce`                  |
|                 | 3d. Analyze + acceptance     | Analyze baseline, propose `config.json`, and present Phase 3 checkpoint | Drive directly                        |
| **4. Plan**     | 4-pre. Architecture review   | Confirm work type, source of truth, sub-skills, iteration model, validation model, and comparison model | `adlc-execute`                        |
|                 | 4-pre2. Strategy review      | Classify failure layer, compare viable strategies, and identify hard gates | `adlc-execute`                        |
|                 | 4a. Triage                   | Score blast radius, classify (ship/proctor/spike)         | `adlc-execute`                        |
|                 | 4b. Test matrix              | Define test counts, thresholds, max iterations            | `adlc-execute`                        |
|                 | 4c. Present plan             | Show plan, get user approval                              | `adlc-execute`                        |
| **5. Execute**  | 5.1. Edit instruction        | Write compacted text, save to attempts folder             | `adlc-execute` + relevant Salesforce skill |
|                 | 5.2. Deploy instruction      | Update instruction in org + backup/readback safeguards; use `.agent` validate/publish when source of truth is an authoring bundle | `developing-agentforce`, `observing-agentforce`, or local UI-built exception |
|                 | 5.3. Run smoke test          | 3-5 utterance quick validation                            | `testing-agentforce`                  |
|                 | 5.4. Evaluate smoke          | Check pass rate against threshold                         | `adlc-execute`                        |
|                 | 5.5. Run bulk eval           | Full utterance set, export CSV                            | `testing-agentforce`                  |
|                 | 5.6. Run regression          | Compare new CSV vs baseline CSV                           | `adlc/scripts/generate_report.py`    |
|                 | 5.7. Acceptance check        | Evaluate current-stage blocking criteria, pull user if ambiguous | `adlc-execute`                  |
|                 | 5.8. Iterate or stop         | Decide: fix and loop back to 5.1, or exit                 | `adlc-execute`                        |
| **6. Present**  | 6a. Generate report          | HTML/JSON eval report from regression data                | `adlc/scripts/generate_report.py`    |
|                 | 6b. Write status             | Update `status.md` / final recommendation notes and `config.json` results | `adlc-execute`      |
|                 | 6c. Present to user          | Show GO/NO-GO/CONDITIONAL recommendation                  | `adlc-execute`                        |
| **7. Hand off** | 7a. Rollback if needed       | Restore baseline instruction                              | `observing-agentforce` or local UI-built exception |
|                 | 7b. Promote baseline         | Copy winning attempt to baselines folder                  | `adlc-execute`                        |
|                 | 7c. Remind deploy            | Tell user to use `developing-agentforce` separately       | `adlc-execute`                        |


## Ownership Summary


| Owner             | Steps                                                        | Role                                                                     |
| ----------------- | ------------------------------------------------------------ | ------------------------------------------------------------------------ |
| **adlc-drive**    | 1a, 1d, 2 all, 3 all, Phase 3 handoff                         | Goal refinement, canonical discovery, baseline/test setup, proposed acceptance state |
| **adlc-execute**  | 4 all, 5 all, 6 all, 7 all                                     | Plan, edit/test/evaluate loop, final recommendation, handoff              |
| **developing-agentforce** | 1c                                                   | Find agent/topic metadata, author/scaffold/deploy/publish when needed    |
| **observing-agentforce**  | 3b, 5.2, 7a                                          | Read/write instructions, trace/behavior analysis, rollback support       |
| **testing-agentforce**    | 3c, 5.3, 5.5                                         | Preview smoke, Testing Center operations, action execution               |
| **Shared script** | 5.6, 6a                                                      | `adlc/scripts/generate_report.py` — regression comparison + HTML report |
| **JIRA MCP**      | 1b                                                           | Read-only ticket access via `user-atlassian`                             |


## Sub-Skill Requirements

### developing-agentforce (1c)

- Query `BotDefinition`, `GenAiPlannerDefinition`, `GenAiPluginDefinition` to resolve agent/topic names
- Return: agent API name, topic developer names, plugin definition IDs
- **Local overlay:** If no usable authoring bundle exists, resolve UI-built agent/topic records via SOQL per `adlc/docs/core-process-overlay.md`.

### observing-agentforce (3b, 5.2, 7a)

- **3b:** Read instruction source from `.agent` by default after metadata/source-of-truth is resolved. For UI-built agents with no usable authoring bundle, read `GenAiPluginInstructionDef` through the local exception path. Return instruction text, word count, rollback source, and structure findings.
- **5.2:** Update through `.agent` validate/publish by default. For approved UI-built exceptions, update `GenAiPluginInstructionDef` via Tooling API with backup/readback safeguards.
- **7a:** Rollback — restore instruction from backup file or prior accepted attempt.
- **Local overlay:** Direct Tooling API writes are an project-specific exception, not Salesforce standard guidance.

### testing-agentforce (3c, 5.3, 5.5)

- **3c:** Build fresh test specs from canonical baseline utterances, ticket examples, and derived cases; create/run the baseline suite and export CSV.
- **5.3/5.5:** Create YAML spec → `sf agent test create` → `sf agent test run` → `sf agent test results` → export CSV.
- Handles contextVariables (routable ID) when needed.
- **Local overlay:** Save raw CSV/JSON outputs and compare with `adlc/scripts/generate_report.py` using consistent decoding/reporting conventions.

### Shared Scripts

- `adlc/scripts/generate_report.py` — Regression report engine. Computes scorecard (wins/regressions/ties), strategy distribution, formatting compliance, opening behavior, response length buckets, multi-turn awareness, consistency, tool-calling, latency/safety/quality sections when present, and a filtered response comparison appendix. Outputs HTML + optional JSON sidecar (`--json-output`). Topic-agnostic; topic-specific analysis (tool accuracy, template adherence, GO/NO-GO) is handled by the AI in Phase 6.

## Current State Artifacts

| Artifact | Owner | Purpose |
|---|---|---|
| `hitl.jsonl` | `adlc-drive` / `adlc-execute` | Durable approvals, corrections, process deviations, and risk acceptance |
| `discovery.json` | `adlc-drive`, updated by `adlc-execute` as needed | Durable machine-readable handoff: source of truth, IDs, canonical folder, baseline CSV, config path, suite name, diagnostic mode |
| `config.json` | `adlc-drive`, finalized by `adlc-execute` | Acceptance criteria lifecycle, thresholds, stages, and Phase 6 per-criterion results |
| `.adlc-drive-state.json` | local session only | Resumability scratchpad; not an audit or closeout artifact |

`discovery.json` and `config.json` are the durable handoff state. `.adlc-drive-state.json` exists only to resume interrupted work and should be reconciled into ticket artifacts before handoff or closeout.
