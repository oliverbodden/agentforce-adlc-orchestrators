# ADLC Core Process Overlay

Local project overlay for ticket-driven Agentforce improvement. This document describes process requirements that sit above Salesforce upstream skills. It does not replace or modify Salesforce standard skills.

Use this overlay when coordinating work through local `adlc-drive`, `adlc-execute`, `adlc-ticket`, or future wrapper/orchestrator workflows.

---

## Overlay Boundaries

Salesforce upstream provides standard implementation capabilities:

- `developing-agentforce`: author, discover, scaffold, deploy, safety, feedback.
- `testing-agentforce`: preview tests, Testing Center batch tests, action execution.
- `observing-agentforce`: STDM/session trace analysis, reproduce, optimize.

Project local overlay provides process controls:

- Ticket readiness and scope refinement.
- HITL decisions and audit trail.
- Discover dependency map.
- Solution Strategy Review.
- Baseline and eval artifact conventions.
- Product acceptance and technical review.
- Corporate artifact repo submission.
- Monthly skill-improvement review.

Rule: standard Salesforce skill content is not modified or deleted directly. Add local behavior through wrapper skills, overlay docs, patch files with markers, or bootstrap install steps.

---

## UI-Built Agent Exception Path

Salesforce upstream skills treat `.agent` authoring bundles as the preferred source of truth and warn against direct edits to generated/internal agent metadata. That is the default for pro-code agents and any agent with a reliable authoring-bundle path.

Your organization may still have UI-built agents where the live editable instruction surface exists only in org metadata such as `GenAiPluginInstructionDef`. For those agents, local ADLC may use a narrow Tooling API exception path, but only under these conditions:

- Phase 3 discovery confirms the affected agent/topic has no usable `.agent` authoring bundle path.
- The work is limited to existing instruction text or read-only discovery. Do not use this exception to create new topics, actions, flows, Apex, routing surfaces, or prompt-template behavior.
- Originals are saved before analysis or editing, including record IDs and exact instruction text.
- Each change updates one logical instruction surface at a time and saves an attempt artifact before deployment.
- Rollback is a direct restore from the saved original or previous accepted attempt.
- HITL is required if both `.agent` and UI-built metadata paths appear to exist, if source-of-truth is ambiguous, or if the requested change can be done through an authoring bundle.

Minimum UI-built discovery evidence:

- Resolve `BotDefinition` / active agent version and org alias.
- Resolve affected `GenAiPluginDefinition` topic records.
- Resolve affected `GenAiPluginInstructionDef` records, labels, descriptions/instructions, and parent topic relationships.
- Record whether an authoring bundle exists locally or can be retrieved/published safely.

Minimum Tooling API edit safeguards:

- Query and save current record values before any write.
- Never store `sf org display` access tokens in artifacts.
- PATCH only the approved instruction field on the approved `GenAiPluginInstructionDef` record.
- Immediately read back the record and smoke test live behavior.
- Log the exception decision, record IDs, deployment result, and rollback path in HITL or the attempt metadata.

This exception belongs to the local overlay and wrappers. Do not copy it into Salesforce standard skills unless Salesforce upstream adopts the same policy.

---

## Phase Ownership

Use the existing wrapper skill phase numbers, with human-facing aliases that make the workflow easier to reason about:


| Local phase                       | Purpose                                                                                                                                                | Upstream capability used                                                              |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------- |
| `1. Goal / Understand`            | Understand request, readiness, business goal, initial scope, and known agent/org/version claims                                                        | Local wrapper plus optional JIRA MCP                                                  |
| `2. Refine`                       | Confirm scope, assumptions, org/agent/version, context needs, and SPIKE gate before machine discovery                                                  | Local wrapper                                                                         |
| `3. Discover`                     | Resolve live agent structure, save originals, build dependency map, build full prompt mental model, design tests, and generate fresh baseline evidence | `developing-agentforce`, `observing-agentforce`, `testing-agentforce`, Salesforce CLI |
| `4. Plan`                         | Choose architecture/root-cause surface, prompt strategy, options, risks, test matrix, iteration budget, and rollback                                   | Local wrapper using architecture and prompt playbooks                                 |
| `5. Execute + Iterative Evaluate` | Make one logical approved change per iteration, smoke test, evaluate, and autonomously fix diagnosable in-scope failures                               | Upstream skill based on strategy plus `testing-agentforce`                            |
| `6. Present Final Evaluation`     | Produce final regression, ticket-goal, feature, scenario, product, and technical/process evidence with recommendation                                  | Local wrapper plus eval report and governance overlay                                 |
| `7. Approval + Hand Off`          | Record GO / NO-GO / CONDITIONAL approval, artifact package, HITL summary, baseline promotion guidance, and repo routing                                | Local wrapper                                                                         |


---

## Discover Dependency Map

Discovery must produce a dependency map before strategy planning. The map prevents invalid test plans and prompt-only fixes for action/data/environment problems.

Minimum fields:


| Field                    | Description                                                                          |
| ------------------------ | ------------------------------------------------------------------------------------ |
| `agent`                  | Agent label/API name/version/org.                                                    |
| `topics_or_subagents`    | Affected topic/subagent names and routing/classification notes.                      |
| `instructions`           | Global and topic instruction records or `.agent` instruction locations.              |
| `actions`                | Available and expected actions, invocation names, descriptions, input/output fields. |
| `targets`                | Flow, Apex, API, prompt template, retriever, or metadata targets.                    |
| `variables`              | Linked, mutable, session, user, account, contact, and custom variables.              |
| `data_dependencies`      | CRM records, sandbox seed data, knowledge indexes, external systems.                 |
| `auth_and_permissions`   | Default agent user, permissions, connected app access, tokens, expiring credentials. |
| `environment_gaps`       | Differences between lower env and production.                                        |
| `testability`            | Per requirement/scenario classification.                                             |
| `recommended_validation` | Preview, Testing Center, deterministic unit test, STDM, live proctor, or sign-off.   |


For prompt-facing work, Discovery must also produce a prompt mental model after originals are saved and before strategy planning. Minimum fields:


| Field                            | Description                                                                                                                |
| -------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| `prompt_purpose`                 | What the current prompt is trying to make the agent do.                                                                    |
| `prompt_structure`               | Major phases/sections such as Understand, Gather, Build, escalation, output rules, and final checks.                       |
| `control_flow`                   | Where the prompt classifies intent, asks clarification, calls tools, handles tool output, and composes the final response. |
| `tool_interaction`               | Actions, input/output fields, prompt templates, retrievers, and utility actions that influence behavior.                   |
| `load_bearing_scaffolding`       | Store blocks, checkpoints, templates, and verification rules that should not be removed casually.                          |
| `conflicts_and_insertion_points` | Contradictions, ticket conflicts, and safe targeted edit locations.                                                        |
| `structure_assessment`           | `targeted-edit-safe`, `messy-but-workable`, or `restructure-recommended`.                                                  |


Testability classifications:

- `fully-testable-lower-env`
- `partially-testable-lower-env`
- `requires-prod-like-data`
- `requires-token-or-context`
- `requires-external-system`
- `not-lower-env-testable`

Hard rule: a scenario that cannot be tested accurately in the available environment is not passed. It is excluded with a caveat, validated through another approved path, or accepted as residual risk with product/technical sign-off.

---

## Solution Strategy Review

Run this review after Discover and before implementation planning.

Required questions:

1. What failure class best explains the evidence?
2. Is the issue actually in instructions, or in routing, action selection, action execution, data/RAG, context, environment, or product definition?
3. Is the current topic/subagent the correct surface?
4. Does the ticket-requested approach conflict with architecture evidence?
5. Which 2-3 strategies are viable?
6. Which strategy is recommended and why?
7. What validation path proves the strategy worked?
8. What cannot be tested in lower env?
9. If prompt-facing, does the prompt mental model support a targeted edit, or is restructure justified?

Strategy choices:


| Strategy                             | Use when                                                                            |
| ------------------------------------ | ----------------------------------------------------------------------------------- |
| Instruction edit                     | Desired behavior is governed by topic/global instructions and required data exists. |
| Action description/field description | Tool selection or field use is ambiguous.                                           |
| Topic/subagent routing change        | Classification boundaries are wrong or overlapping.                                 |
| New/reused action                    | Agent lacks the capability or should call deterministic logic.                      |
| Flow/Apex/API fix                    | Backing action errors, returns wrong data, or lacks required behavior.              |
| Retriever/RAG fix                    | Retrieval source, chunking, freshness, or query behavior is wrong.                  |
| Test/context setup                   | Failure is caused by missing lower-env data, tokens, routable IDs, or permissions.  |
| Product clarification                | Correct behavior is undefined or business rules conflict.                           |
| SPIKE                                | Evidence is insufficient to choose safely.                                          |


Hard gate conditions:

- Recommended strategy contradicts the ticket.
- Product behavior changes.
- Eval criteria are flipped or relaxed.
- Routing/topic boundaries change.
- New action/topic/data work is required.
- Lower-env cannot validate a critical scenario.
- Salesforce docs and live org evidence conflict.
- Prompt restructure is recommended.

HITL must record the decision, evidence, source docs if used, trade-offs, and next step.

Prompt restructure is a high-blast-radius strategy. Prefer targeted edits unless the prompt is clearly contradictory/messy, targeted edits are unsafe, or repeated approved iterations failed because prompt structure appears to be the blocker.

---

## Testing Model

Keep deterministic code tests, ticket-goal validation, bulk regression, bulk feature eval, and scenario simulation separate.


| Layer                        | Purpose                                                | Typical tool                                               |
| ---------------------------- | ------------------------------------------------------ | ---------------------------------------------------------- |
| Deterministic unit tests     | Validate Flow/Apex/API/helper behavior in isolation    | Apex tests, Flow tests, API tests                          |
| Ticket-goal validation tests | Quickly test the specific change before bulk evals     | `sf agent preview`, small Testing Center suite             |
| Bulk regression evals        | Protect unchanged behavior                             | Testing Center static cases and baseline utterances        |
| Bulk feature evals           | Validate ticket-specific new/changed behavior at scale | Testing Center static cases                                |
| Scenario simulation          | Test realistic multi-turn engagement and branching     | Live turn-by-turn simulation or static history when stable |


Terminology:

- `Utterance`: one user input.
- `Test case`: one eval item, either single-turn or static multi-turn with `conversationHistory`.
- `Scenario`: a described user journey that may include branching.
- `Bulk eval population`: the comparable set used for baseline vs new runs.

If a team says "500 scenarios," clarify whether they mean 500 utterances, 500 static test cases, or 500 live scenario journeys.

Phase placement:

- Phase 3 creates fresh baseline evidence and approved test specs.
- Phase 5 runs smoke tests and evaluates each iteration; diagnosable in-scope failures loop back into execution without HITL.
- Phase 5 runs broader evals only after smoke tests pass.
- Phase 6 presents final evaluation and recommendation.
- Phase 7 records approval and handles artifact/baseline/repo handoff.

HITL is not required for every failed test or ordinary regression. HITL is required when results are ambiguous, the fix changes scope or strategy, product behavior or eval criteria must change, a hard gate is reached, or the approved max iterations are exhausted.

---

## Utterance And Scenario Selection

For both ticket-goal validation and bulk evals:

- Start with stored baseline utterances for affected topics.
- Include adjacent topics when routing may shift.
- Map every ticket requirement and acceptance criterion to at least one utterance or scenario.
- Add derived utterances when baselines are insufficient.
- Include negative and boundary cases when guardrails, refusals, escalation, or data handling are affected.
- Track provenance: `baseline`, `ticket-example`, `derived-from-requirement`, `edge-case`, `scenario-step`, or `adversarial`.
- Avoid adding volume without coverage value.

Multi-turn guidance:

- Use static Testing Center `conversationHistory` when the prior state is known and deterministic.
- Use live scenario simulation when the goal depends on the agent's actual prior response or branching behavior.
- Keep live scenario simulation separate from deterministic regression unless the path is stable enough to encode as static test cases.

---

## Eval Separation

Bulk eval reports must separate:

- Overall GO / NO-GO / CONDITIONAL recommendation.
- Overall metrics.
- Regression metrics for unchanged behavior.
- Ticket-specific metrics for the requested goal.
- Scenario metrics, split by static multi-turn vs live simulation.
- Coverage mapping from requirements to utterances/scenarios.
- Comparability caveats.
- Environment/testability caveats.

Baseline vs new must be apples-to-apples wherever possible:

- Same test population.
- Same scenario definitions.
- Same context variables.
- Same static history representation.
- Same run count target.
- Same scoring logic unless a change was approved.
- Same result export/parsing convention. If Testing Center output is HTML-encoded, scoring/reporting must decode it consistently before comparison.

If cases are added, removed, skipped, or changed, separate comparable and non-comparable metrics.

Local reporting conventions:

- Save raw CSV/JSON outputs under the ticket attempt or baseline folder.
- Use `adlc/scripts/generate_report.py` for comparable baseline-vs-new reports when available.
- Keep Salesforce Testing Center mechanics in `testing-agentforce`; keep project report interpretation, HTML unescape policy, and artifact layout in this overlay and the project report scripts.

---

## Drive-To-Execute Handoff

Each drive run should maintain a lightweight `discovery.json` in the ticket folder once Phase 3a begins. This file is the machine-readable handoff from `adlc-drive` to `adlc-execute`; prose artifacts remain the source of reasoning, but execute should not have to infer core IDs from narrative text.

`discovery.json` is durable ticket state. It belongs in the ticket folder and should travel with the artifact package. `.adlc-drive-state.json` is a local resumability scratchpad in the project root; use it to recover an interrupted session, but do not treat it as authoritative for source of truth, canonical folder, diagnostic mode, acceptance criteria, or final recommendation. When the two disagree, stop for HITL and reconcile into `discovery.json`, `config.json`, and `hitl.jsonl`.

Minimum fields:

- `agent_api_name`
- `agent_dev_name`
- `org_alias`
- `topic_names`
- `plugin_definition_ids`
- `instruction_def_ids`
- `has_authoring_bundle`
- `source_of_truth`
- `canonical_ticket_folder`
- `baseline_csv`
- `testing_center_suite_name`
- `config_json`
- `goal_md`
- `dependency_map`
- `prompt_mental_model`

Use `null` plus a short reason for fields that do not apply, such as `testing_center_suite_name` when the run used preview-only smoke tests. If `source_of_truth`, instruction IDs, baseline CSV, config path, or canonical folder are ambiguous, stop for HITL before handing off to execute.

---

## Acceptance Criteria State

Each drive run should create `config.json` in Phase 3d after baseline analysis and before the Phase 3 checkpoint. At that point the criteria are proposed. After the user approves the Phase 3 checkpoint, `config.json` becomes the authoritative acceptance state for Phase 4-6. Any later criteria change requires HITL and a `config.json` update.

Keep the shape lightweight. The goal is durable acceptance state, not a scoring engine.

Minimum top-level fields:

- `ticket`
- `agent`
- `org`
- `topic`
- `source_of_truth`
- `current_stage`
- `approved_checkpoint`: `null` until Phase 3 approval, then the approving checkpoint such as `phase_3`
- `approved_at`: `null` until Phase 3 approval, then an ISO8601 timestamp
- `eval.baseline_csv`
- `eval.regression_spec`
- `eval.ticket_goal_spec`
- `acceptance_criteria`

Each criterion should include:

- `id`: stable reference, such as `ac-001`
- `type`: `regression`, `ticket_goal`, `show_stopper`, `product_acceptance`, or `testability`
- `description`: human-readable criterion
- `priority`: `critical`, `high`, `medium`, or `low`
- `tolerance_preset`: `exact`, `strict`, `standard`, `flexible`, `manual_review`, or `informational`
- optional numeric threshold fields when the criterion needs precision, such as `target`, `min_pass_rate`, or `max_regression_delta`
- `blocking`: whether failure blocks GO for the current stage
- `status`: lifecycle state: `proposed`, `approved`, `changed`, `deferred`, or `waived`
- optional `result`: Phase 6 outcome state, such as `passed`, `failed`, `deferred`, or `waived`, plus evidence
- `stage`: current or future stage when staged execution applies
- `evidence_source`: where Phase 6 should look

Tolerance presets map user-friendly approval language to scoring behavior. They are defaults for human judgment, not a substitute for explicit numbers when the ticket needs precision. If the user approves a numeric threshold during Phase 3 or Phase 4, record it in the criterion and echo it in the readable approval summary.

| Preset | Default meaning |
|---|---|
| `exact` | Must match perfectly; any miss blocks if criterion is blocking |
| `strict` | Tiny variance allowed, usually around >=95% pass |
| `standard` | Normal ADLC tolerance, usually around >=90% pass or <=10% regression |
| `flexible` | Improvement expected, product judgment allowed |
| `manual_review` | Human/product review decides pass/fail |
| `informational` | Track only; does not affect GO/NO-GO |

Phase 6 maps criteria to recommendation:

- `GO`: all blocking criteria for the current approved stage passed, and remaining non-blocking issues are acceptable.
- `CONDITIONAL`: blocking criteria passed, but non-blocking issues, future stages, manual review, or residual risks remain.
- `NO-GO`: any blocking criterion failed, any blocking criterion is deferred without approved staging, criteria changed without HITL, or critical untestable risk lacks sign-off.
- `ABANDONED`: user stops or abandons the run before acceptance.

Staged tickets can be `GO` for the current stage without being ticket-complete. Deferred future-stage criteria must state the stage and reason so they are not misreported as failed.

Phase 6 should write final per-criterion outcomes into `result`, not overwrite the approval lifecycle in `status`. For example: `"result": {"outcome": "passed", "evidence": "eval-report.json:metrics.goal_pass_rate", "notes": "94% pass rate against approved >=90% threshold"}`.

Example criterion:

```json
{
  "id": "ac-001",
  "type": "ticket_goal",
  "description": "Compact prompt to <=70% of baseline size",
  "priority": "critical",
  "tolerance_preset": "exact",
  "target": "<=70% of baseline size",
  "blocking": true,
  "status": "approved",
  "result": null,
  "stage": "stage_1",
  "evidence_source": "attempt_metadata"
}
```

Operational diagnostic mode metadata belongs in `discovery.json`, not `config.json`. `config.json` may reference a diagnostic acceptance criterion if removal/internalization is part of acceptance, but `discovery.json` is the canonical source for the fields below:

```json
"diagnostic_mode": {
  "used": true,
  "reason": "Repeated prompt failures; failure layer unclear",
  "hypothesis": "response construction is ignoring selected strategy",
  "trace_visibility": "user_facing",
  "prompt_stages_logged": ["UNDERSTAND", "GATHER", "BUILD"],
  "control_variables_logged": ["RequestType", "ServiceStrategy", "Goal addressed", "Template", "Closing line"],
  "insertion_points": [
    "top-level requirement",
    "post-tool response format",
    "strategy templates",
    "output rules",
    "diagnostic template",
    "final no-exceptions reminder"
  ],
  "must_remove_before_production": true,
  "removal_verified": false
}
```

---

## Diagnostic Trace Governance

Temporary diagnostic traces are allowed during ADLC development when repeated prompt failures cannot be diagnosed from normal traces, tool outputs, or eval results.

For Agentforce, diagnostic traces may need to be framed as explicit user-facing transparency content to survive the trusted output layer. This is a deliberate diagnostic override, not production behavior.

Requirements:

- HITL approval before adding exposed user-facing diagnostic traces.
- Record the hypothesis for what is causing the failure.
- Record which prompt stages and control variables are logged.
- Record whether the trace is internal-only or user-facing.
- Record all insertion points where the trace was added.
- Mark whether the trace must be removed/internalized before production.
- Before final acceptance, verify the trace has been removed/internalized from every insertion point unless product explicitly approves exposed transparency output.
- When verification is complete, set `diagnostic_mode.removal_verified=true` in `discovery.json`. If product approves exposed transparency to remain, record that approval in HITL and in the Phase 6 diagnostic trace status instead of marking removal verified.

---

## Acceptance And HITL Governance

Final recommendations must follow `adlc/docs/acceptance-eval-hitl-governance.md`.

Minimum closeout expectations:

- Produce a `GO`, `NO-GO`, `CONDITIONAL`, or `ABANDONED` recommendation.
- Tie the recommendation to separate regression, ticket-goal, scenario, product, and technical/process evidence.
- Include apples-to-apples comparability notes when baseline and final runs differ.
- Report lower-env limitations and residual risk explicitly.
- Log HITL entries for hard gates, strategy changes, criteria changes, process deviations, product decisions, environment gaps, and skill-improvement signals.
- If diagnostic traces were used, report whether they were removed/internalized or explicitly approved to remain before final `GO`.
- Do not treat untestable lower-env scenarios as passed.

---

## Artifact And Onboarding Guidance

- Artifact repo workflow: `adlc/docs/artifact-repo-workflow.md`
- Developer onboarding/setup: `adlc/docs/developer-onboarding.md`

Closeout must verify the artifact repo remote before guiding a push or PR. The expected shared repo is `https://github.com/YOUR_ORG/YOUR_ADLC_ARTIFACT_REPO`.

Onboarding must verify Salesforce CLI command surfaces, installed upstream baseline, local overlay docs, and artifact repo routing before declaring a workstation ready.

---

## Relationship To Other Docs

- Architecture/root-cause decisions: `adlc/playbooks/agentforce-architecture-playbook.md`
- Prompt/instruction craft: `adlc/playbooks/prompt-engineering-playbook.md`
- Acceptance/eval/HITL governance: `adlc/docs/acceptance-eval-hitl-governance.md`
- Artifact repo workflow: `adlc/docs/artifact-repo-workflow.md`
- Developer onboarding/setup: `adlc/docs/developer-onboarding.md`
- Upstream/provenance status: `adlc/versioning/`
- Process/delegation map: `adlc/docs/drive-architecture.md`
