# adlc-drive — Architecture & Delegation Map

## Step-by-Step Flow


| Phase           | Step                         | What happens                                              | Calls                                 |
| --------------- | ---------------------------- | --------------------------------------------------------- | ------------------------------------- |
| **1. Goal**     | 1a. Parse input              | Extract ticket key or free text                           | Drive directly                        |
|                 | 1b. Pull JIRA ticket         | Fetch title, description, AC                              | `user-atlassian` MCP → `getJiraIssue` |
|                 | 1c. Find agent/topic in org  | Resolve API names, instruction record IDs                 | `adlc-discover`                       |
|                 | 1d. Normalize goal           | Map JIRA fields to goal structure                         | Drive directly                        |
| **2. Refine**   | 2a. Scope                    | Discuss topics, actions, surfaces with user               | Drive directly                        |
|                 | 2b. SPIKE gate               | Uncertainty check                                         | Drive directly                        |
|                 | 2c. Confirm alignment        | Present summary, get approval                             | Drive directly                        |
| **3. Discover** | 3a. Pull current instruction | Read topic instruction(s) from org                        | `adlc-optimize` Phase 1               |
|                 | 3b. Structural checks        | Dead topics, orphan actions, cross-topic analysis         | `adlc-optimize` Phase 1               |
|                 | 3c. Check existing evals     | Look for recent Testing Center results                    | `adlc-test`                           |
|                 | 3d. Run baseline eval        | Create spec, run tests, export CSV                        | `adlc-test` Mode B                    |
|                 | 3e. Establish acceptance     | Propose criteria from baseline data                       | Drive directly                        |
| **4. Plan**     | 4a. Triage                   | Score blast radius, classify (ship/proctor/spike)         | Drive directly                        |
|                 | 4b. Test matrix              | Define test counts, thresholds, max iterations            | Drive directly                        |
|                 | 4c. Present plan             | Show plan, get user approval                              | Drive directly                        |
| **5. Execute**  | 5.1. Edit instruction        | Write compacted text, save to attempts folder             | Drive directly                        |
|                 | 5.2. Deploy instruction      | Update instruction in org + auto-backup                   | `adlc-optimize`                       |
|                 | 5.3. Run smoke test          | 5-utterance quick validation                              | `adlc-test` Mode B                    |
|                 | 5.4. Evaluate smoke          | Check pass rate against threshold                         | Drive directly                        |
|                 | 5.5. Run bulk eval           | Full utterance set, export CSV                            | `adlc-test` Mode B                    |
|                 | 5.6. Run regression          | Compare new CSV vs baseline CSV                           | `adlc/scripts/generate_report.py`    |
|                 | 5.7. Acceptance check        | Evaluate metrics against criteria, pull user if ambiguous | Drive directly                        |
|                 | 5.8. Iterate or stop         | Decide: fix and loop back to 5.1, or exit                 | Drive directly                        |
| **6. Present**  | 6a. Generate report          | HTML eval report from regression data                     | `adlc/scripts/generate_report.py`    |
|                 | 6b. Write status             | Update CHANGELOG.md, STATUS.md in ticket folder           | Drive directly                        |
|                 | 6c. Present to user          | Show summary, recommendation                              | Drive directly                        |
| **7. Hand off** | 7a. Rollback if needed       | Restore baseline instruction                              | `adlc-optimize`                       |
|                 | 7b. Promote baseline         | Copy winning attempt to baselines folder                  | Drive directly                        |
|                 | 7c. Remind deploy            | Tell user to invoke `adlc-deploy` separately              | Drive directly                        |


## Ownership Summary


| Owner             | Steps                                                        | Role                                                                     |
| ----------------- | ------------------------------------------------------------ | ------------------------------------------------------------------------ |
| **Drive**         | 1a, 1d, 2 all, 3e, 4 all, 5.1, 5.4, 5.7, 5.8, 6b, 6c, 7b, 7c | Brain — goals, decisions, creative edits, acceptance judgment            |
| **adlc-discover** | 1c                                                           | Find agent/topic metadata in org                                         |
| **adlc-optimize** | 3a, 3b, 5.2, 7a                                              | Read/write instructions, structural analysis                             |
| **adlc-test**     | 3c, 3d, 5.3, 5.5                                             | All Testing Center operations                                            |
| **Shared script** | 5.6, 6a                                                      | `adlc/scripts/generate_report.py` — regression comparison + HTML report |
| **JIRA MCP**      | 1b                                                           | Read-only ticket access via `user-atlassian`                             |


## Sub-Skill Requirements

### adlc-discover (1c)

- Query `BotDefinition`, `GenAiPlannerDefinition`, `GenAiPluginDefinition` to resolve agent/topic names
- Return: agent API name, topic developer names, plugin definition IDs
- **Gap:** Currently assumes `.agent` file exists. Needs to support UI-built agents via SOQL.

### adlc-optimize (3a, 3b, 5.2, 7a)

- **3a:** Read `GenAiPluginInstructionDef` for a given topic. Return instruction text + word count.
- **3b:** Structural checks — list all topics, check for dead topics, orphan actions.
- **5.2:** Update `GenAiPluginInstructionDef` via Tooling API. Auto-backup before writing.
- **7a:** Rollback — restore instruction from backup file.
- **Gap:** Currently assumes `.agent` file. Needs Tooling API path for UI-built agents.

### adlc-test (3c, 3d, 5.3, 5.5)

- **3c:** `sf agent test list` — check for existing test suites.
- **3d/5.3/5.5:** Create YAML spec → `sf agent test create` → `sf agent test run` → `sf agent test results` → export CSV.
- Handles contextVariables (routable ID) when needed.
- **Gap:** Mostly works today. Needs to expose CSV export as a standard output.

### Shared Scripts

- `adlc/scripts/generate_report.py` — runs `run_regression.py` with correct paths, wraps in HTML.
- `adlc/scripts/update_instruction.py` — Tooling API deploy + backup. To be replaced by `adlc-optimize` once it supports Tooling API.
- `adlc/scripts/run_eval.py` — Testing Center runner + CSV export. To be replaced by `adlc-test` once it exposes CSV output.

## What Needs to Change


| Sub-skill       | Change needed                                                        | Effort |
| --------------- | -------------------------------------------------------------------- | ------ |
| `adlc-discover` | Added Section 0: SOQL-based agent/topic resolution | Done |
| `adlc-optimize` | Added Section 3.UI: Tooling API read/write/backup/rollback | Done |
| `adlc-test`     | Added CSV export in Phase 3 + HTML unescape guidance | Done |
| `adlc-drive`    | Phase 3 + 5 delegate to sub-skills | Done |
| Shared scripts   | Archived `update_instruction.py`, `run_eval.py`. Kept `generate_report.py` | Done |

