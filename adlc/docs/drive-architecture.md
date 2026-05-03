# adlc-drive — Architecture & Workflow Trace

## Current Status

This map is a current orientation aid, not the authoritative skill text. Current ADLC behavior is governed by:

- `adlc/playbooks/agentforce-architecture-playbook.md`
- `adlc/playbooks/prompt-engineering-playbook.md`
- `adlc/playbooks/eval-report-playbook.md`
- `adlc/docs/core-process-overlay.md`
- `adlc/docs/acceptance-eval-hitl-governance.md`
- `adlc/docs/developer-onboarding.md`
- Local wrapper skills `adlc-drive` and `adlc-execute`
- Salesforce upstream standard skills `developing-agentforce`, `testing-agentforce`, `observing-agentforce` (treated as baseline; never modified directly)

`adlc-drive` owns Phases 1–3 and stops after the Phase 3 handoff. `adlc-execute` owns Phases 4–6. Salesforce skills are execution tools; they do not replace the wrapper phases.

---

## Workflow Trace

Each numbered step lists the file read/written, folder created, CLI command, REST API, or MCP call invoked. One sentence per step, in execution order, starting when the user invokes `adlc-drive`.

### Phase 1 — Goal (adlc-drive)

1. **read** `~/.cursor/skills/adlc-drive/SKILL.md` — orchestrator loads its own instructions.
2. **read once** `adlc/playbooks/agentforce-architecture-playbook.md`, `adlc/playbooks/prompt-engineering-playbook.md`, `adlc/docs/core-process-overlay.md`, and `adlc/docs/acceptance-eval-hitl-governance.md` — local overlays for the session.
3. **read** `~/.cursor/skills/adlc-ticket/SKILL.md` — assess ticket readiness when the user provides a JIRA ticket or ticket-like text.
4. **MCP call** `user-atlassian.getAccessibleAtlassianResources` and `user-atlassian.getJiraIssue` — only for JIRA input.
5. **output** Phase 1 summary in chat — no org queries, no user gate, no artifact folder.

### Phase 2 — Refine (adlc-drive)

6. **output** architecture context from the already-loaded overlays — short note before asking questions.
7. **conversation** — confirm scope, agent name, org alias, topic(s), and edit strategy; do not require agent version here.
8. **CHECKPOINT — wait for user approval** of scope boundaries, split/SPIKE/proceed decision, open questions, and planned working folder path.
9. **No folder created yet** — Phase 3a creates the canonical folder after live metadata confirms `BotDefinition.DeveloperName`.

### Phase 3 — Discover (adlc-drive)

10. **read** `~/.cursor/skills/developing-agentforce/SKILL.md` — resolve agent/topic metadata and authoring-bundle status.
11. **CLI calls** `sf data query ...` and `sf project retrieve ...` — resolve `BotDefinition`, topic/plugin records, instruction record IDs, active version, org identity, and source of truth.
12. **HITL if needed** — canonical name mismatch, ambiguous source of truth, unexpected topic/instruction shape, or version conflict with user intent.
13. **mkdir/write** canonical `adlc/agents/<agent-dev-name>__<org-alias>/`, ticket folder, `meta.json`, `goal.md`, `hitl.jsonl`, and initial `discovery.json`.
14. **read** prior canonical `hitl.jsonl` files under the same agent/org folder — summarize relevant prior corrections in `goal.md`.
15. **read** `~/.cursor/skills/observing-agentforce/SKILL.md` or reuse developing-agentforce discovery guidance — pull current instructions/structure based on work type.
16. **write** `originals/` rollback artifacts — exact instruction text or source-agent structure before any analysis or editing.
17. **write** `discovery-context.md` — prompt mental model for instruction edits plus dependency map for all work types.
18. **read** `~/.cursor/skills/testing-agentforce/SKILL.md` — build fresh regression/capability specs from baseline utterances, ticket examples, and derived coverage.
19. **CLI call** `sf agent test create/run ...` or preview flow — run fresh baseline against live current behavior.
20. **write/update** `baseline.csv`, `specs/`, and `discovery.json` fields for baseline path and Testing Center suite name.
21. **read** `adlc/playbooks/eval-report-playbook.md` and **CLI call** `python3 adlc/scripts/generate_report.py --prev baseline.csv --new baseline.csv --output /tmp/baseline-analysis.html` — baseline feature profile.
22. **write** `config.json` — proposed acceptance criteria with lifecycle fields.
23. **CHECKPOINT — wait for user approval** of discovery findings, test plan, baseline metrics, acceptance criteria, caveats, and assumptions.
24. **update/append** approved `config.json` statuses and `hitl.jsonl` approval entry.

### Hand Off (adlc-drive → adlc-execute)

25. **append** `hitl.jsonl` — `{"phase":"3-handoff","type":"context","decision":"Entering Phase 4 via adlc-execute"}`.
26. **read** `~/.cursor/skills/adlc-execute/SKILL.md` — Phase 4 starts inside that skill.

### Phase 4 — Plan (adlc-execute)

27. **read overlays only if needed** — same-session handoffs rely on the Phase 1 overlay reads; fresh resumptions load them once.
28. **read** `discovery.json`, `goal.md`, `discovery-context.md`, `config.json`, and `hitl.jsonl` — Phase 3 handoff state.
29. **append** `hitl.jsonl` — architecture review and solution strategy review.
30. **CHECKPOINT — wait for user approval** of strategy, plan, test/execution parameters, risk, rollback, and design-review tag if applicable.

### Phase 5 — Execute + Iteratively Evaluate (adlc-execute)

For each iteration:

31. **append** `hitl.jsonl` — entering iteration and selected execution skill.
32. **read/use** the selected Salesforce skill: `observing-agentforce` for instruction edits, `developing-agentforce` for authoring/scaffold/publish, or `testing-agentforce` for validation.
33. **mkdir/write** `attempts/<NN>-<name>/` artifacts, including candidate instruction/source and raw outputs when available.
34. **apply** one logical change through the approved source-of-truth path.
35. **unit test** 2-4 target utterance variants, 3-4 runs each.
36. **smoke test** 2-4 regression canaries, 2-3 runs each.
37. **bulk eval** after unit and smoke pass — run the approved full set and generate `attempts/<NN>/eval-report.{html,json}` with `generate_report.py`.
38. **acceptance check** against `config.json` — continue, stop for HITL, or proceed to Phase 6.
39. **write** `.adlc-drive-state.json` — local resumability scratchpad only.
40. **append** `hitl.jsonl` — iteration outcome and decision.

### Phase 6 — Present Final Evaluation + Closeout (adlc-execute)

41. **read/use** `acceptance-eval-hitl-governance.md` and `eval-report-playbook.md` — final acceptance and report interpretation.
42. **CLI call** `python3 adlc/scripts/generate_report.py --prev baseline.csv --new <winner>.csv --output <ticket>/eval-report.html --json-output <ticket>/eval-report.json --title "<goal>" [--master <expected-values.csv>]`.
43. **read** `eval-report.json` and **update** `config.json` result fields per criterion.
44. **write** `status.md` / final recommendation notes.
45. **CHECKPOINT — wait for user approval** of GO/NO-GO/CONDITIONAL recommendation and evidence.
46. **closeout after approval** — optional baseline promotion, optional rollback if user asks, optional baseline utterance updates if approved, artifact package validation, diagnostic trace verification, and `.adlc-drive-state.json` cleanup.
47. **append** `hitl.jsonl` — final approval and closeout decision.
48. **STOP** — deployment/publish/activation is a separate user decision through `developing-agentforce`.

---

## Ownership Summary

| Owner | Steps in trace | Role |
|---|---|---|
| **adlc-drive** | Phases 1–3 + handoff | Goal, refine, discover, baseline + acceptance proposal, handoff. |
| **adlc-execute** | Phases 4–6 | Plan, edit-test-evaluate loop, final recommendation, closeout. |
| **adlc-ticket** | Phase 1 | Ticket-readiness assessor. |
| **developing-agentforce** | Phases 3 and 5 | Resolve org metadata; author/scaffold/deploy/publish when selected. |
| **observing-agentforce** | Phases 3, 5, and optional closeout | Read/edit instructions via `.agent` or the approved Tooling API exception; optional rollback if user asks. |
| **testing-agentforce** | Phases 3 and 5 | Build test specs, run baseline, unit/smoke validation, and bulk Testing Center runs. |
| **`adlc/playbooks/eval-report-playbook.md`** | Phases 3, 5, and 6 | Central evaluation guidance, including scoring, Testing Center CSV triage, support benchmark rubrics, and report interpretation. |
| **`adlc/scripts/generate_report.py`** | Phases 3, 5, and 6 | Single ADLC eval/report script (baseline CSV + candidate CSV → HTML/JSON). |
| **`user-atlassian` MCP** | Phase 1 | Read-only JIRA access. |

---

## Sub-Skill Quick Reference

| Skill | Loaded By | Primary CLI/API surface it owns | Sub-references it loads |
|---|---|---|---|
| `adlc-drive` | User / skill invocation | This file is the orchestrator. | `examples/phase-outputs.md` |
| `adlc-ticket` | `adlc-drive` Phase 1 | None (analytical). | `adlc/ticket-guides/{ticket-authoring-prompt, ticket-evaluation-samples, ticket-template, ticket-template-generalfaq, ticket-rewrites-internal}.md` |
| `developing-agentforce` | `adlc-drive` Phase 3; `adlc-execute` Phase 5 when selected | `sf data query`, `sf project retrieve`, `sf agent generate`, `sf agent publish`. | `references/{discover-reference, salesforce-cli-for-agents, agent-metadata-and-lifecycle, agent-design-and-spec-creation, agent-script-core-language, agent-validation-and-debugging, scaffold-reference, deploy-reference, architecture-patterns, …}.md` + `assets/*.agent` patterns |
| `observing-agentforce` | `adlc-drive` Phase 3; `adlc-execute` Phase 5 when selected | `.agent` file edits + Tooling API `GenAiPluginInstructionDef` PATCH. | `references/{issue-classification, reproduce-reference, improve-reference, stdm-queries, stdm-schema}.md` + `apex/AgentforceOptimizeService.cls` |
| `testing-agentforce` | `adlc-drive` Phase 3; `adlc-execute` Phase 5 when selected | `sf agent test create/run/results`, `sf agent preview start/send/end`. | `references/{preview-testing, batch-testing, action-execution, test-report-format, troubleshooting}.md` + `assets/{basic,standard,guardrail}-test-spec.yaml` |
| `adlc-execute` | `adlc-drive` handoff or fresh resumption | Orchestrator for Phases 4–6. | `examples/phase-outputs.md` |

---

## Current State Artifacts

| Artifact | Owner | Purpose |
|---|---|---|
| `hitl.jsonl` | `adlc-drive` + `adlc-execute` | Durable approvals, corrections, process deviations, risk acceptance (one file per ticket). |
| `discovery.json` | `adlc-drive` (created); `adlc-execute` (updated) | Durable machine-readable handoff: source_of_truth, IDs, canonical folder, baseline CSV, config path, suite name, diagnostic mode. |
| `config.json` | `adlc-drive` (proposed); `adlc-execute` (Phase 6 results) | Acceptance criteria lifecycle, thresholds, stages, per-criterion results. |
| `goal.md` + `discovery-context.md` | `adlc-drive` (Phase 3) | Human-readable handoff context — `goal.md` for scope/WHY, `discovery-context.md` for technical findings (mental model + dependency map). |
| `originals/<topic>-<id>.txt` | `adlc-drive` (Phase 3b) | Rollback source-of-truth — never modified after creation. |
| `attempts/<NN>-<name>/{instruction.txt, raw-outputs.csv, eval-report.{html,json}}` | `adlc-execute` (Phase 5) | Per-iteration evidence. |
| `eval-report.{html,json}` (ticket root) | `adlc-execute` (Phase 6) | Final deterministic eval report. |
| `status.md` | `adlc-execute` (Phase 6) | Final recommendation notes. |
| `.adlc-drive-state.json` (project root, gitignored) | local session only | Resumability scratchpad — not audit, not handoff. |
| `baselines/<topic>/utterances.txt` | `adlc-drive` (read) + `adlc-execute` Phase 6 closeout (append) | Permanent test inputs across versions. |
| `baselines/v<N+1>/` | `adlc-execute` Phase 6 closeout | Version snapshot when promoted to prod. |

---

## Not Touched By Default

These files or locations are read-only unless an explicit phase step, bootstrap command, or user approval says otherwise:

| Path / Location | Default Handling |
|---|---|
| `adlc/skills/upstream/**` | Do not edit directly. Bootstrap updates vendored upstream skills through `--update-upstream-skills`. |
| `~/.cursor/skills/**` | Do not modify during normal ADLC runs. Bootstrap installs missing skills; manual sync/removal requires explicit user approval. |
| `adlc/agents/<agent>__<org>/tickets/<ticket>/originals/**` | Never modify after capture. Originals are rollback evidence. |
| `force-app/**` | Do not edit unless the approved Phase 4 plan selects an authoring/scaffold/deploy path. |
| Production agent metadata / org state | Do not deploy, publish, activate, or rollback automatically. These are separate user-approved actions. |
| Existing ticket folders | Treat as append-only unless the user explicitly confirms resuming that exact run. |
