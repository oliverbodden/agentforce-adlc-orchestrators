---
name: adlc-drive
description: >-
  Goal-driven Agentforce agent improvement. Takes a goal or requirement,
  refines it collaboratively, discovers baseline state, then hands off to
  adlc-execute for planning and iterative execution. Use when the user has
  a goal, improvement, bug fix, or feature request for an Agentforce agent.
---

# ADLC Drive

Orchestrate goal-driven agent improvements: from intake through discovery
to a verified baseline. This skill owns Phases 1-3 (Goal, Refine, Discover).
Once discovery is complete and the user approves, it delegates Phases 4-7
(Plan, Execute, Present, Hand Off) to `adlc-execute`.

Drive owns the *what* and *why*; it delegates the *how* to other ADLC skills.

---

## 0. LOCAL OVERLAY DOCS

Before running this skill in an Agentforce project, read the local overlay docs if they exist:

- `adlc/playbooks/agentforce-architecture-playbook.md` — architecture, root-cause taxonomy, dependency mapping, strategy freshness.
- `adlc/docs/core-process-overlay.md` — project ADLC overlay boundaries, Discover dependency map, testing model, eval separation.
- `adlc/docs/acceptance-eval-hitl-governance.md` — HITL categories, acceptance governance, testability reporting, monthly improvement signals.

If these docs are missing, continue with this skill but note the gap in HITL. Do not modify Salesforce upstream standard skill files directly; local behavior belongs in wrappers, overlays, project playbooks, or approved additive patches.

---

## 1. RULES (apply to all phases, including adlc-execute)

**⛔ TRANSPARENCY RULE: Commit to decisions in writing BEFORE acting on them.** For every significant decision (which phase to enter, which skill to call, what to change, what to test, whether to proceed or stop), write out:
1. What you decided
2. Why (your reasoning — not restating instructions, but explaining your logic)
3. What you're about to do next

This is visible to the user as you work. It serves two purposes: the user catches wrong assumptions in real time, and you can't contradict your own reasoning (if you wrote "ServiceStrategy = EXPLAIN" you can't then generate an ESCALATE response).

**⛔ CHECKPOINT RULE: Phases that need user approval MUST pause and wait.** Phases that are just showing work can continue. The per-phase instructions below specify which checkpoints pause and which are output-only.

**⛔ PROCESS FAILURE RECOVERY: When the user identifies a process failure, STOP all work.** Re-read the FULL requirements for the current phase. Audit every requirement against your actual actions — not just the one the user flagged. Log ALL gaps found to HITL. Only resume after the audit is logged and the user confirms.

**⛔ HITL LOG RULE: Append a JSONL entry to the ticket's `hitl.jsonl` IMMEDIATELY after each of these events:**
- User responds to a checkpoint (type: approval/correction/rejection)
- User provides information (type: context)
- Agent generates significant analysis — triage, blast radius, test matrix, plan options, acceptance criteria (type: context)
- Process failure is identified (type: process-failure)
- Session ends early (type: early-exit)

File: `adlc/agents/{agent-dev-name}__{org-alias}/tickets/{key}/hitl.jsonl` — lives with the ticket, one file per ticket, no central index.

HITL is the single source of truth for the session — not chat, not separate files.

Entry format: `{"ts":"<ISO8601>","session_id":"<chat-id>","phase":"<N-name>","checkpoint":"<what>","type":"<approval|correction|rejection|context|escalation|early-exit|process-failure>","asked":"<what you presented>","decision":"<what user said>","agent":"<agent>","topic":"<topic>","ticket":"<key>","who":"<user>","org":"<org>","agent_version":"<version>","edit_strategy":"<strategy>"}`. Include `org`, `agent_version`, and `edit_strategy` from Phase 2 onward. Log the interaction as it happened — do not sanitize or summarize the user's words.

**Pending HITL before ticket folder exists:** Because Phase 1 intentionally does not create the final ticket folder, any HITL-worthy Phase 1 or pre-Phase-2-approval event must be tracked as pending HITL in the visible conversation. As soon as the working ticket folder exists after Phase 2 approval, backfill those pending entries into `hitl.jsonl` before continuing to Phase 3. Do not create the final folder early just to satisfy HITL logging.

**Delegation map:**

| Capability | Delegated to |
|---|---|
| Evaluate ticket readiness, help write tickets | `adlc-ticket` |
| Trace analysis and standard `.agent` instruction optimization | `observing-agentforce` |
| UI-built instruction read/write with no usable authoring bundle | Local `core-process-overlay.md` UI-built exception path, orchestrated by `adlc-drive` / `adlc-execute` |
| Run tests, bulk evals, export results, execute actions | `testing-agentforce` |
| Resolve agent/topic metadata in org | `developing-agentforce` |
| Generate missing Flow/Apex stubs | `developing-agentforce` |
| Build new agent or major rewrite | `developing-agentforce` |
| Plan, execute iterations, present results, hand off | `adlc-execute` |
| Deploy, publish, activate | `developing-agentforce` (user invokes separately when needed) |

---

## 2. PHASES

### Phase 1: Goal / Understand

Capture what the user wants to achieve. The human-facing alias is `Understand`: know the business request, ticket readiness, and initial assumptions before asking refinement questions or proposing a solution.

**Input:** One of:
- JIRA ticket key/URL → auto-pull goal, requirements, attachments (see Section 4)
- Open text → user describes the goal directly

If no ticket, ask the user to describe the goal in detail. Read the ticket or description and formulate your own understanding — different tickets need different questions.

**Evaluate ticket readiness:**

→ Read `~/.cursor/skills/adlc-ticket/SKILL.md`
  You need: evaluate if this ticket has enough context for drive to execute
  Execute the assessment. If verdict is "Not ready" or "Out of scope", stop and tell the user.
  If "Needs improvement", present gaps and ask user to fill them before proceeding.
  If "Ready" or "Ready with gap", continue.

Do **not** create the final agent-scoped ticket folder during Phase 1. At this point the ticket may contain a display name, stale org alias, or incorrect agent claim. Keep the Phase 1 understanding in chat until Phase 2 confirms the operating context.

**Agent folder naming (`agents/{agent-dev-name}__{org-alias}`):**
- Use the agent's `DeveloperName` (from `BotDefinition`), not the kebab-cased display label. This guarantees uniqueness within an org.
- Append `__{org-alias}` (double underscore separator) to disambiguate agents with the same developer name across different orgs.
- If the agent folder doesn't exist yet, create it and write a `meta.json` at the agent-folder root with: `agent_dev_name`, `agent_label`, `bot_definition_id`, `org_alias`, `org_id`, `org_instance_url`, `created`, and any session notes.
- Legacy folders (e.g. `adlc/example-service-agent/`) predate this convention. Prefer migrating them to `adlc/agents/{agent-dev-name}__{org-alias}/` after confirming the canonical developer name and org alias.

**Work item folder naming (`{ticket-key}-{short-description}` or `NOTICKET-NN-{short-description}`):**
- Ticketed work: use the real key (e.g. `HELP-1234-fix-escalation`).
- Ticketless work: use `NOTICKET-NN-{short-description}` where `NN` is a zero-padded running counter scoped **per agent folder** (start at `01`, increment by looking at existing `NOTICKET-*` dirs under `tickets/`), and `{short-description}` is at most 4 words in kebab-case. Example: `NOTICKET-01-match-prod-v2`.

After Phase 2 approval, create the working ticket folder at `adlc/agents/{confirmed-agent-name}__{confirmed-org-alias}/tickets/{ticket-key}-{short-description}/` and document the Phase 1/2 understanding in `goal.md`.

All durable ticket artifacts go in the working/canonical ticket folder. I know you'll want to create it at the project root or in a `tickets/` shortcut — don't. Every durable artifact must live under `adlc/agents/{agent-dev-name}__{org-alias}/tickets/` or it gets lost.

**⛔ CHECKPOINT (output only — no questions yet, no org queries):**
- Your understanding of the goal (in your own words)
- Ticket readiness assessment
- What you know vs what you still need to find out
- Any assumptions you're making and WHY

Then immediately proceed to Phase 2 — that's where questions happen.

### Phase 2: Refine

Collaborative back-and-forth to ensure alignment before any work starts.

**Before asking questions, read `adlc/playbooks/agentforce-architecture-playbook.md` and `adlc/docs/core-process-overlay.md` if present.** Then read the architecture summary in `adlc/playbooks/prompt-engineering-playbook.md` only as prompt-craft context. Understand topics/subagents, actions, instructions, templates, data flow, dependencies, and testability before asking questions.

**Then refine through conversation.** Based on your Phase 1 understanding, the ticket content, and the architecture, formulate questions that cover what you need to know to proceed. Don't use a fixed list — reason from context. I know you'll want to infer the agent name, version, org, and edit strategy from files like `agent-meta.json` — don't. Always ask the user explicitly. These are critical parameters that change between sessions and wrong assumptions here cascade through every subsequent phase.

**SPIKE gate:** At any point during refinement, if the problem or solution is unclear, propose a SPIKE — a time-boxed investigation that produces findings, not changes. If SPIKE, present the investigation plan and stop. Do not proceed to Phase 3.

**Prompt-scope split check:** For prompt-facing tickets with multiple acceptance criteria, assess prompt modification breadth before proceeding:
- If one requirement broadly compacts, rewrites, or restructures a prompt section, and another requirement is style/output polish, recommend splitting into separate tickets or making the structural work a clearly separate first-stage ticket.
- If multiple requirements are localized output-style rules on the same response surface and share the same eval path, keep one ticket but plan staged execution.
- If requirements touch multiple topics/actions, do not split automatically. First identify whether a shared global instruction surface intentionally owns the behavior. If yes, use that global surface with representative canaries; if no, recommend splitting by topic/action or getting explicit staged approval.
- Present the split/stage recommendation during Phase 2 so the user can approve scope before discovery and planning.

**⛔ CHECKPOINT:** Present to user and wait for approval:
- Your understanding of the full scope (in your own words)
- What's in scope vs what you're explicitly NOT touching (and why)
- Prompt-scope split/stage recommendation, when the ticket is prompt-facing and has multiple acceptance criteria
- SPIKE gate decision (proceed or investigate)
- The confirmed agent name, org alias, topic(s), agent version if known, edit strategy, and the working ticket folder path you will create after approval
- Any open questions or concerns
- Any assumptions and WHY

### Phase 3: Discover

Gather evidence about the current state. This is where the machine starts investigating — Phases 1-2 were human conversation only. Discover must produce enough evidence for Phase 4 to choose a strategy without guessing.

**3a-pre. Preliminary prior HITL scan:**

If Phase 2 confirmed a likely agent/org folder, you may do a preliminary scan of prior ticket folders under that path for `hitl.jsonl` entries matching the agent and/or topic. Treat this as advisory only because the canonical `BotDefinition.DeveloperName` has not been verified yet. Do not treat "no prior HITL found" as final until after 3a canonical metadata resolution.

**3a. Resolve agent/topic metadata:**

→ Read `~/.cursor/skills/developing-agentforce/SKILL.md`
  You need: how to resolve agent and topic IDs for a Salesforce org (may or may not have an authoring bundle)
  Use the agent name and topics confirmed by the user in Phase 2.
  Store: agent_api_name, plugin_definition_id, instruction_def_ids, has_authoring_bundle, and source_of_truth (`authoring-bundle`, `ui-built-tooling-api`, or `ambiguous`)

If authoring-bundle status is unknown, missing, or likely UI-built, also read `adlc/docs/core-process-overlay.md` section "UI-Built Agent Exception Path" before resolving metadata. Use both Salesforce standard discovery guidance and the local overlay evidence requirements to classify `source_of_truth`.

**Canonical folder verification:** After resolving canonical metadata, compare the confirmed working folder against `adlc/agents/{BotDefinition.DeveloperName}__{org-alias}/tickets/{ticket-key}-{short-description}/`. If the folder does not exist yet, create it now and write/update `goal.md`. If a provisional working folder already exists under a non-canonical agent name or org alias, stop for HITL before moving or duplicating artifacts. Log the final canonical folder decision to HITL.

**3a-post. Canonical prior HITL lookup:**

After canonical metadata and folder path are resolved, check prior ticket folders under `adlc/agents/{BotDefinition.DeveloperName}__{org-alias}/tickets/*/hitl.jsonl` for entries matching this agent and/or affected topic(s). Look for patterns: recurring corrections, prior rejections, known gotchas from earlier drives, source-of-truth decisions, and prior process failures. Summarize relevant findings in the ticket's `goal.md` under a "Prior HITL context" heading. If the canonical lookup contradicts the preliminary scan, trust the canonical lookup and log the correction to HITL.

**Source-of-truth gate:** Use Salesforce's `.agent` / authoring-bundle path by default when it exists and can safely publish the affected agent. Use the local UI-built Tooling API exception only when discovery confirms there is no usable authoring-bundle path. Before using the exception, read `adlc/docs/core-process-overlay.md` section "UI-Built Agent Exception Path" and document why the exception applies. If both paths appear possible or conflict, HITL before continuing.

**Discovery handoff artifact:** Create or update `discovery.json` in the ticket folder after 3a and keep it current through 3d. It must include at minimum: `agent_api_name`, `agent_dev_name`, `org_alias`, `topic_names`, `plugin_definition_ids`, `instruction_def_ids`, `has_authoring_bundle`, `source_of_truth`, `canonical_ticket_folder`, `baseline_csv`, `testing_center_suite_name` if one is created, `config_json`, and pointers to `goal.md`, `dependency-map.md` / `prompt-mental-model.md` when those are split out. If diagnostic mode is used later, `adlc-execute` must update this file with the `diagnostic_mode` object described in `adlc/docs/core-process-overlay.md`. This is the machine-readable handoff for `adlc-execute`.

If discovery reveals surprises (more instruction records than expected, unexpected topic structure, agent version mismatch), HITL — present findings and re-confirm scope with user before continuing.

**3b. Pull current state + audit for conflicts:**

Use the agent/topic IDs resolved in step 3a. The approach depends on the work type confirmed in Phase 2:

**For instruction edits (modifying an existing agent's topic instructions):**

**Save the original instruction text immediately** — before any analysis or editing. Store each instruction record as-is in the ticket folder:
```
adlc/agents/{agent-dev-name}__{org-alias}/tickets/{key}/originals/
  {topic-name}-{record-id}.txt
```
These are the rollback point. Never modify the originals folder.

→ Read `~/.cursor/skills/observing-agentforce/SKILL.md`
  You need: how to analyze the current instruction and trace/behavior surface.
  If `source_of_truth=authoring-bundle`, read instructions from the `.agent` source. If `source_of_truth=ui-built-tooling-api`, follow the local UI-built exception path in `adlc/docs/core-process-overlay.md` to read the approved `GenAiPluginInstructionDef` records. Store: instruction text, word count for ALL affected instruction records (global + per-topic), record IDs, source_of_truth, and rollback source.

**For new agent authoring or major rewrite (creating an agent that replicates/replaces an existing one):**

Use `developing-agentforce` discovery guidance (already run in 3a) to map the **source agent's** full structure: all topics, actions per topic, action targets (flows, prompt templates, apex), variables (linked and mutable), and system-level instructions. Store the structure snapshot in the ticket folder:
```
adlc/agents/{agent-dev-name}__{org-alias}/tickets/{key}/originals/
  source-agent-structure.md
```
This is the reference the authoring skill will use. For each topic, save the source instruction text from the confirmed source of truth. If the source is UI-built metadata, follow the local UI-built exception path in `adlc/docs/core-process-overlay.md` for read-only capture so the authored agent can replicate behavior faithfully.

**Then, for both paths:**

Audit: do any existing instructions or structures contradict the new guidelines? Flag conflicts (e.g., existing instruction says "use Here's what I found" but ticket says remove it). Document conflicts in goal.md.

**Full prompt mental model (required before 3c):**

After originals are saved and before baseline/test design, read the full affected prompt/instruction set and `adlc/playbooks/prompt-engineering-playbook.md`. Build a prompt mental model in `goal.md` or `prompt-mental-model.md` under the ticket folder:
- Prompt purpose: what the prompt is trying to make the agent do
- Structure: major phases/sections such as `UNDERSTAND`, `GATHER`, `BUILD`, escalation, output rules, and final quality checks
- Control flow: where the prompt classifies intent, decides whether to ask clarification, calls tools/actions, handles tool output, and composes the final response
- Tool/action interaction: which action descriptions, input fields, output fields, prompt templates, retrievers, or utility actions influence behavior
- Load-bearing scaffolding: `Store:` fields, required checkpoints, fixed templates, or final verification blocks that must not be removed casually
- Existing coverage: where the current prompt already tries to satisfy the ticket goal, if anywhere
- Conflicts and contradictions: instructions that compete with each other or with the ticket
- Candidate insertion points: where a targeted prompt edit could safely live
- Structure assessment: `targeted-edit-safe`, `messy-but-workable`, or `restructure-recommended`

Do not recommend restructure by default. Mark `restructure-recommended` only if the current prompt is clearly contradictory/messy, targeted edits are unsafe, or repeated approved iterations have failed because structure appears to be the blocker. If restructure is recommended, HITL is required in Phase 4 before implementation because blast radius is higher.

**Discover dependency map (required before 3c):**

Using `adlc/playbooks/agentforce-architecture-playbook.md` and `adlc/docs/core-process-overlay.md`, document the dependency map in `goal.md` or a dedicated `dependency-map.md` under the ticket folder:
- Agent, org, version, and affected topics/subagents
- Routing/classification surfaces and adjacent topics that may be affected
- Global/topic instructions and action references
- Actions, backing targets, input fields, output fields, and expected tool usage
- Variables, session/user/account/contact context, routable IDs, permissions, tokens, connected systems, and retriever/RAG sources
- Lower-env vs production gaps
- Per-requirement testability classification: `fully-testable-lower-env`, `partially-testable-lower-env`, `requires-prod-like-data`, `requires-token-or-context`, `requires-external-system`, or `not-lower-env-testable`
- Recommended validation path for each caveated requirement

If any critical scenario is not lower-env testable, HITL before treating the ticket as executable. Do not count untestable scenarios as passed.

Then continue to 3c.

**3c. Establish baseline + build test utterances:**

Do NOT adopt pre-existing Testing Center test suites — build fresh from baseline utterances.

**Baseline utterances live in ONE place only:** `adlc/agents/{agent-dev-name}__{org-alias}/baselines/{topic}/utterances.txt`
Do NOT search Downloads, project root, old ticket folders, or anywhere else for baseline data. If the utterance file doesn't exist for a topic, ask the user to provide one or derive utterances from the instruction.

**Baseline folder matching (required before using utterances):** After Phase 3a discovery, list existing folders under `adlc/agents/{agent-dev-name}__{org-alias}/baselines/` and match them against the topics discovered from the org. Flag mismatches: folders with no matching topic, topics with no matching folder, or multiple folders that map to a single topic. Present findings to the user and confirm which folder to use before proceeding. Do NOT silently pick a folder — a wrong match means testing the wrong utterances.

**Baseline = utterances, not outputs.** I know you'll want to reuse an old CSV of outputs as the baseline to save time — don't. Org state changes between runs make old outputs invalid. Always run utterances against the live instruction to generate fresh outputs.

**Context variables check (HARD GATE):** Does this topic need session context (e.g., linked variables, account data, user identity) for testing? Ask the user — they know which topics need context vs which are self-contained. If context is needed, **STOP and ask the user what variables are required and their current values.** Do NOT proceed with testing if a topic needs context and you don't have it — results will be invalid. See playbook testing section for details.

**Combine ALL available sources for the test spec (AND, not OR):**
1. **Baseline utterances** (from `adlc/agents/{agent-dev-name}__{org-alias}/baselines/{topic}/utterances.txt`) → regression tests
2. **Ticket attachments** → examples of bad/new behavior
3. **Derived from instruction + requirements** → edge cases, gaps

**Coverage check:** Map every ticket requirement to at least one test utterance. If a requirement has no utterance exercising it, derive one.

**Multi-turn awareness:** Consider if the goal changes behavior across turns. For each requirement, classify:
- "First response changes" → single-turn test
- "Follow-up behavior changes" → multi-turn test (use `conversationHistory` in YAML spec)
- Topics that naturally require multiple turns (e.g., selecting an item then explaining it) need multi-turn even for single-turn changes

**Guardrails:**
- Minimum 5 multi-turn test cases per ticket (catches conversation continuity issues)
- Maximum ~50 utterances per ticket. If the change is comprehensive and needs more, HITL — ask user if scope should be split.

**Split eval criteria into three buckets:**
1. **Regression (unchanged)** — existing criteria that still apply as-is
2. **Regression (modified)** — existing criteria the ticket changes. These move to ticket eval AND update regression for QA.
3. **New ticket criteria** — entirely new metrics from requirements

Store regression spec and capability spec separately in `specs/`.

**Run the baseline now.** Use `testing-agentforce` to run the regression utterances against the live instruction and export results as CSV. This is the fresh baseline — save it to the ticket folder as `baseline.csv`. This CSV is what Phase 3d analyzes.

Record the Testing Center suite API name / eval definition name in `discovery.json` as `testing_center_suite_name` when Testing Center is used. If the baseline uses preview-only smoke instead, set this field to `null` and record the reason.

**3d. Analyze baseline and establish acceptance criteria:**

Before proposing criteria, analyze the baseline CSV to understand current metrics:
- Run `python3 adlc/scripts/generate_report.py --prev <baseline.csv> --new <baseline.csv> --output /tmp/baseline-analysis.html` (comparing baseline to itself gives you the feature profile)
- Or manually: count utterances, compute response feature rates, check redundancy, measure response lengths
- Identify which metrics are relevant for THIS topic (not all topics have the same features)

Then propose acceptance criteria based on goal type:

```
Baseline: X utterances, key features: [list discovered from CSV]

Proposed criteria:
  1. Regression: no existing metric drops more than [threshold from ticket, default 10%]
  2. Goal-specific: [derived from the goal — e.g., "bad experience fixed in N/N cases" or "new behavior works in >X% of relevant utterances"]
  3. Show-stoppers: [from ticket AC]
  4. New test utterances (if applicable): [list]
```

Create `config.json` in the ticket folder using the lightweight acceptance-state shape from `adlc/docs/core-process-overlay.md`. Each criterion must have at minimum `id`, `type`, `description`, `priority`, `tolerance_preset`, `blocking`, `status`, `stage` when applicable, and `evidence_source`. Add optional numeric threshold fields such as `target`, `min_pass_rate`, or `max_regression_delta` when the user needs precision beyond the preset. Keep Phase 6 outcome fields such as `result` empty until evaluation. Criteria are `proposed` until the Phase 3 checkpoint is approved.

When presenting criteria to the user, do not ask them to review raw JSON line-by-line. Present the readable summary: criterion, priority, tolerance preset, explicit numeric thresholds if any, blocking/non-blocking, stage, evidence source, and caveats. After approval, update criterion statuses to `approved`, set `approved_checkpoint` and `approved_at`, and log the HITL decision. Later criteria changes require HITL and a `config.json` update.

**⚠️ HITL required** when existing eval criteria are being modified or flipped. The user must confirm that changing what "good" means was intentional — product or dev may not have reviewed the implications of flipping a metric.

**⛔ CHECKPOINT — do NOT present until ALL of the following are complete:**
- 3a: Metadata resolved ✓
- 3b: Instructions pulled, originals saved, analysis checklist done, and prompt mental model documented ✓
- 3c: Test specs built (utterances + coverage check + multi-turn) ✓
- 3d: Baseline run, metrics analyzed, acceptance criteria proposed ✓

**Then present to user and wait for approval:**
- Instruction analysis per topic (from checklist)
- Conflicts found
- Prompt mental model: structure, control flow, tool/action interaction, load-bearing scaffolding, insertion points, and structure assessment
- Discover dependency map and testability classifications
- Test specs built (utterance counts, multi-turn count, coverage gaps)
- Baseline metrics (from fresh run, not stale data)
- Eval criteria split: unchanged / modified / new
- Proposed acceptance thresholds
- Exit ramps (anything out of scope)
- Assumptions and WHY

### Hand off to adlc-execute

**⛔ HARD GATE — do NOT skip this step.** Once the user approves Phase 3:

1. **STOP.** Do not continue planning, editing, authoring, or debugging inline.
2. **Log to HITL:** `{"phase":"3-handoff","type":"context","decision":"Entering Phase 4 via adlc-execute"}` — this creates an audit trail that the handoff happened.
3. **Read `~/.cursor/skills/adlc-execute/SKILL.md` NOW.** Do not proceed without reading it. Phase 4 starts inside that skill.

All discovery artifacts, acceptance criteria, and conversation context carry forward.

**⛔ Salesforce skills do NOT replace adlc-execute.** Skills like `developing-agentforce`, `observing-agentforce`, and `testing-agentforce` are execution tools that adlc-execute orchestrates during Phase 5. They are NOT standalone phases. If you just finished using a Salesforce skill to generate, edit, deploy, or test an agent, you are NOT done — adlc-execute still owns the test-evaluate-iterate loop, publish validation, and acceptance check. Going ad-hoc after a sub-skill call is the #1 process failure mode.

---

## 3. RESUMPTION

If a session breaks mid-execution, check for `.adlc-drive-state.json` at startup:

```bash
if [ -f .adlc-drive-state.json ]; then
  echo "Found in-progress drive session"
  cat .adlc-drive-state.json
fi
```

If found, offer to resume:

```
I found an in-progress drive session:
  Goal: <goal>
  Phase: <phase>, iteration <N>
  Current pass rate: <X%>

Resume from where we left off, or start fresh?
```

Before resuming, read the ticket folder's `discovery.json` if present and reconcile it with `.adlc-drive-state.json`. If `diagnostic_mode.used=true`, surface that in the resume summary, including `trace_visibility`, `hypothesis`, active insertion points, and whether `removal_verified` is false. Treat `discovery.json` as the source of truth for diagnostic metadata unless HITL explicitly corrects it. If state and discovery disagree on source of truth, diagnostic mode, canonical folder, or active attempt, stop for HITL before editing.

`.adlc-drive-state.json` is only a local resumability scratchpad. Do not use it as the durable audit or handoff source. Before handing off or closing out, make sure durable state is reflected in the ticket folder: `discovery.json` for source-of-truth/IDs/diagnostic mode, `config.json` for acceptance criteria, and `hitl.jsonl` for approvals and decisions.

---

## 4. JIRA INTEGRATION

### Connection

Uses the official Atlassian MCP server (`user-atlassian`) via OAuth SSO. No credentials stored locally.

**First use:** Call `getAccessibleAtlassianResources` to discover available cloud IDs. Store the cloud ID for subsequent calls. If multiple resources exist, ask the user which one.

### Allowed Tools (READ-ONLY)

| Tool | Purpose |
|---|---|
| `getJiraIssue` | Fetch a ticket by key |
| `searchJiraIssuesUsingJql` | Search tickets with JQL |
| `getVisibleJiraProjects` | List projects |
| `searchAtlassian` | Full-text search |

**⛔ NEVER call these tools:** `createJiraIssue`, `editJiraIssue`, `addCommentToJiraIssue`, `transitionJiraIssue`, `addWorklogToJiraIssue`, `createIssueLink`. This skill is read-only.

### Usage

When user provides a JIRA key or URL, call `getJiraIssue` with the discovered `cloudId` and extract goal, requirements, and attachments from the ticket fields. If auth fails, call `mcp_auth` to trigger browser SSO. Use the ticket key for the eval folder name.
