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
Once discovery is complete and the user approves, it delegates Phases 4-6
(Plan, Execute, Present/Closeout) to `adlc-execute`.

Drive owns the *what* and *why*; it delegates the *how* to other ADLC skills.

---

## 0. LOCAL OVERLAY DOCS — read ONCE per session

At the start of an `adlc-drive` session, read these overlay docs (if they exist) one time and rely on them for the rest of the session. Per-phase instructions will refer back to these without telling you to re-read them.

- `adlc/playbooks/agentforce-architecture-playbook.md` — architecture, root-cause taxonomy, dependency mapping, strategy freshness.
- `adlc/playbooks/prompt-engineering-playbook.md` — prompt-craft principles, editing patterns, diagnostics (loaded in full because Phase 3b and Phase 5 both rely on it).
- `adlc/docs/core-process-overlay.md` — Indeed ADLC overlay boundaries, Discover dependency map, testing model, eval separation.
- `adlc/docs/acceptance-eval-hitl-governance.md` — HITL categories, acceptance governance, testability reporting, monthly improvement signals.

If a doc is missing, continue with this skill but note the gap in HITL. Do not modify Salesforce upstream standard skill files directly; local behavior belongs in wrappers, overlays, project playbooks, or approved additive patches.

**Re-reading rule:** Only re-read an overlay doc within a single session if (a) it has been modified during the session, (b) the user explicitly says to re-load it, or (c) you have evidence you've drifted from its guidance.

---

## 1. RULES (apply to all phases, including adlc-execute)

**⛔ TRANSPARENCY RULE: Commit to decisions in writing BEFORE acting on them.** For every significant decision (which phase to enter, which skill to call, what to change, what to test, whether to proceed or stop), write out:
1. What you decided
2. Why (your reasoning — not restating instructions, but explaining your logic)
3. What you're about to do next

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

Entry format: `{"ts":"<ISO8601>","session_id":"<chat-id>","phase":"<N-name>","checkpoint":"<what>","type":"<approval|correction|rejection|context|escalation|early-exit|process-failure>","asked":"<what you presented>","decision":"<what user said>","agent":"<agent>","topic":"<topic>","ticket":"<key>","who":"<user>","org":"<org>","agent_version":"<version>","edit_strategy":"<strategy>"}`. Include `org` and `edit_strategy` from Phase 2 onward; add `agent_version` once Phase 3a discovers it. Log the interaction as it happened — do not sanitize or summarize the user's words.

**Pending HITL before ticket folder exists:** Phase 1 + Phase 2 HITL events stay pending in chat; Phase 3a backfills them into `hitl.jsonl` when the canonical folder is created. Don't create the folder early to satisfy logging — that was the original failure mode (folders under guessed-at names).

Each phase below specifies which sub-skill to call inline (e.g., "→ Read `~/.cursor/skills/developing-agentforce/SKILL.md`"). For a full delegation reference, see `adlc/docs/drive-architecture.md` Sub-Skill Quick Reference.

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

Do **not** create any agent or ticket folder during Phase 1 or Phase 2. Keep all Phase 1 + Phase 2 understanding in chat. Folder creation happens in Phase 3a (folder naming conventions are defined there).

**Phase 1 Summary (output only — no user gate, no org queries, no questions yet):** Output and continue immediately.

- Your understanding of the goal (in your own words)
- Ticket readiness assessment
- What you know vs what you still need to find out
- Any assumptions you're making and WHY

### Phase 2: Refine

Collaborative back-and-forth to ensure alignment before any work starts.

**Architecture context (output before asking questions):** Drawing on the overlay docs already loaded in Section 0, write a 2-3 sentence note in chat covering the relevant architecture for this ticket — what topics/subagents are involved, the relevant actions/templates/data flow, and any obvious dependencies or testability concerns.

**Then refine through conversation.** Based on your Phase 1 understanding, the ticket content, and your architecture context note, formulate questions that cover what you need to know to proceed. Don't use a fixed list — reason from context. Do NOT infer agent name, org, or edit strategy from files (e.g. `agent-meta.json`); ask the user explicitly. (Agent version is *not* required at Phase 2; Phase 3a discovers it from `BotDefinition`.)

**Risk-reduction gate (split, spike, or proceed?):** Before locking scope, decide which path this ticket should take:
- **Split** — if the ticket bundles structural prompt rewrite with style polish, spans multiple unrelated topics without a shared global surface, or otherwise asks for too much in one iteration. Recommend splitting into separate tickets or staged execution and present the recommendation at the checkpoint.
- **SPIKE** — if the problem or solution has unknowns that require a time-boxed investigation (producing findings, not changes) before execution can be planned safely. Present the SPIKE plan and stop; do not proceed to Phase 3.
- **Proceed** — if scope is bounded and the path forward is clear enough to plan against.

**⛔ CHECKPOINT:** Present to user and wait for approval:
- Your understanding of the full scope (in your own words)
- Scope boundaries: (a) in scope, (b) adjacent but explicitly NOT touching this iteration, (c) out of scope entirely
- Risk-reduction decision: split / SPIKE / proceed (with reasoning)
- User-confirmed agent name, org alias, topic(s), edit strategy, and the **planned** working ticket folder path (created in Phase 3a after canonical metadata lookup)
- Any open questions or concerns
- Any assumptions and WHY

### Phase 3: Discover

Gather evidence about the current state. Discover must produce enough evidence for Phase 4 to choose a strategy without guessing.

**3a. Resolve canonical metadata, create folder, write handoff state:**

→ Read `~/.cursor/skills/developing-agentforce/SKILL.md`
  You need: how to resolve agent and topic IDs for a Salesforce org (may or may not have an authoring bundle)
  Use the agent name and topics confirmed by the user in Phase 2 as the input.
  Store: `agent_api_name`, `agent_dev_name` (canonical `BotDefinition.DeveloperName`), `plugin_definition_id`, `instruction_def_ids`, `has_authoring_bundle`, and `source_of_truth` (`authoring-bundle`, `ui-built-tooling-api`, or `ambiguous`).

**Three HITL triggers in 3a — STOP for HITL if any fire before creating the folder:**

1. **Canonical name reconciliation:** If canonical `BotDefinition.DeveloperName` differs from the name the user confirmed in Phase 2, present both names and ask the user to confirm which is correct.
2. **Source-of-truth gate:** Use Salesforce's `.agent` / authoring-bundle path by default when it exists and can safely publish the affected agent. Use the local UI-built Tooling API exception only when discovery confirms there is no usable authoring-bundle path; consult the "UI-Built Agent Exception Path" section of `adlc/docs/core-process-overlay.md` (already loaded in Section 0) and document why the exception applies. If both paths appear possible or conflict, HITL.
3. **Discovery surprises:** If 3a reveals more instruction records than expected, unexpected topic structure, or an agent version that conflicts with the user's stated intent, present findings and re-confirm scope with the user.

**Folder naming conventions:**

- **Agent folder** `adlc/agents/{agent-dev-name}__{org-alias}/` — `{agent-dev-name}` = `BotDefinition.DeveloperName` from canonical SOQL (NOT user-typed name or display label); `__{org-alias}` separator disambiguates same-named agents across orgs.
- **Ticket folder** `tickets/{ticket-key}-{short-description}/` for ticketed work (e.g. `HELP-1234-fix-escalation`), or `tickets/NOTICKET-NN-{short-description}/` for ticketless work (`NN` is a zero-padded counter scoped per agent folder, starting at `01`; `{short-description}` is at most 4 words in kebab-case).

All durable ticket artifacts must live under `adlc/agents/{agent-dev-name}__{org-alias}/tickets/` — never at the project root or in a top-level `tickets/` shortcut.

**Create the canonical folder NOW.** Once canonical metadata is resolved (and reconciled if any HITL fired), create:

- `adlc/agents/{agent_dev_name}__{org_alias}/` (if it doesn't exist) and write `meta.json` with: `agent_dev_name`, `agent_label`, `bot_definition_id`, `org_alias`, `org_id`, `org_instance_url`, `created`, and any session notes.
- `adlc/agents/{agent_dev_name}__{org_alias}/tickets/{ticket-key}-{short-description}/` and write `goal.md` documenting the Phase 1+2 understanding (scope, WHY, acceptance intent — keep it scope-focused; technical findings go in `discovery-context.md` later).
- `adlc/agents/{agent_dev_name}__{org_alias}/tickets/{ticket-key}-{short-description}/hitl.jsonl` and **backfill all pending HITL events from Phases 1 and 2** before logging anything new.
- `adlc/agents/{agent_dev_name}__{org_alias}/tickets/{ticket-key}-{short-description}/discovery.json` — machine-readable handoff for `adlc-execute`. Required fields: `agent_api_name`, `agent_dev_name`, `org_alias`, `topic_names`, `plugin_definition_ids`, `instruction_def_ids`, `has_authoring_bundle`, `source_of_truth`, `canonical_ticket_folder`, `baseline_csv` (set in 3c), `testing_center_suite_name` (set in 3c, or `null`), `config_json` (set in 3d), and pointers to `goal.md` and `discovery-context.md`. Keep current through 3d. `adlc-execute` may add `diagnostic_mode` later per `adlc/docs/core-process-overlay.md`.

**Prior HITL lookup (single pass, canonical only):** After the folder is created, check prior ticket folders under `adlc/agents/{agent_dev_name}__{org_alias}/tickets/*/hitl.jsonl` for entries matching this agent and/or affected topic(s). Look for: recurring corrections, prior rejections, known gotchas, source-of-truth decisions, prior process failures. Summarize relevant findings in `goal.md` under a "Prior HITL context" heading.

**3b. Pull current state, audit conflicts, build discovery context:**

Use the agent/topic IDs resolved in 3a. The approach depends on the work type confirmed in Phase 2.

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

Audit: do any existing instructions contradict the new guidelines? Flag conflicts (e.g., existing instruction says "use Here's what I found" but ticket says remove it). Document conflicts in `discovery-context.md` (created below).

**For new agent authoring or major rewrite (creating an agent that replicates/replaces an existing one):**

Use `developing-agentforce` discovery guidance (already run in 3a) to map the **source agent's** full structure: all topics, actions per topic, action targets (flows, prompt templates, apex), variables (linked and mutable), and system-level instructions. Store the structure snapshot in the ticket folder:
```
adlc/agents/{agent-dev-name}__{org-alias}/tickets/{key}/originals/
  source-agent-structure.md
```
This is the reference the authoring skill will use. For each topic, save the source instruction text from the confirmed source of truth. If the source is UI-built metadata, follow the local UI-built exception path in `adlc/docs/core-process-overlay.md` for read-only capture so the authored agent can replicate behavior faithfully.

Audit: does the source agent's structure conflict with the requested replacement? Flag missing pieces (e.g., source uses an action the new authoring scope doesn't include). Document conflicts in `discovery-context.md` (created below).

**Build `discovery-context.md` (required before 3c):**

After originals are saved and audited, write `adlc/agents/{agent-dev-name}__{org-alias}/tickets/{key}/discovery-context.md`. It contains two sections.

**Section 1 — Prompt Mental Model** (instruction edits only; skip entirely for new agent authoring):
- Prompt purpose: what the prompt is trying to make the agent do
- Structure: major phases/sections such as `UNDERSTAND`, `GATHER`, `BUILD`, escalation, output rules, final quality checks
- Control flow: where the prompt classifies intent, decides whether to ask clarification, calls tools/actions, handles tool output, composes the final response
- Tool/action interaction: which action descriptions, input fields, output fields, prompt templates, retrievers, utility actions influence behavior
- Load-bearing scaffolding: `Store:` fields, required checkpoints, fixed templates, final verification blocks that must not be removed casually
- Existing coverage: where the current prompt already tries to satisfy the ticket goal, if anywhere
- Conflicts and contradictions: instructions that compete with each other or with the ticket (cross-reference the audit above)
- Candidate insertion points: where a targeted prompt edit could safely live
- Structure assessment: `targeted-edit-safe`, `messy-but-workable`, or `restructure-recommended`

Do not recommend restructure by default. Mark `restructure-recommended` only if the current prompt is clearly contradictory/messy, targeted edits are unsafe, or repeated approved iterations have failed because structure appears to be the blocker. If restructure is recommended, HITL is required in Phase 4 before implementation because blast radius is higher.

**Section 2 — Dependency Map** (always required, both paths):
- Agent, org, and affected topics/subagents
- Routing/classification surfaces and adjacent topics that may be affected
- Global/topic instructions and action references
- Actions, backing targets, input fields, output fields, expected tool usage
- Variables, session/user/account/contact context, routable IDs, permissions, tokens, connected systems, retriever/RAG sources
- Lower-env vs production gaps
- Per-requirement testability classification: `fully-testable-lower-env`, `partially-testable-lower-env`, `requires-prod-like-data`, `requires-token-or-context`, `requires-external-system`, or `not-lower-env-testable`

Discovery classifies testability; Phase 4 (`4-pre2` Solution Strategy Review) decides the validation path for each caveated requirement.

If any critical scenario is `not-lower-env-testable`, HITL before treating the ticket as executable. Do not count untestable scenarios as passed.

**3c. Establish baseline + build test utterances:**

Do NOT adopt pre-existing Testing Center test suites — build fresh from baseline utterances.

**Baseline utterances live in ONE place only:** `adlc/agents/{agent-dev-name}__{org-alias}/baselines/{topic}/utterances.txt`
Do NOT search Downloads, project root, old ticket folders, or anywhere else for baseline data. If the utterance file doesn't exist for a topic, ask the user to provide one or derive utterances from the instruction.

**Baseline folder matching:** If baseline folder names don't exactly match topic names from 3a, OR multiple folders could map to one topic, OR a topic has no matching folder — HITL the user before picking. Otherwise proceed silently. Wrong match means testing the wrong utterances, but the common case (well-named folders, 1:1 match) doesn't need user input.

**Baseline = utterances, not outputs.** Old CSVs are invalid because org state changes between runs — always run utterances against the live instruction to generate fresh outputs.

**Context variables check (HARD GATE):** If the topic needs session context (linked variables, account data, user identity) for testing, **STOP and ask the user what variables are required and their current values** before testing. See playbook testing section for details.

**Combine ALL available sources for the test spec (AND, not OR):**
1. **Baseline utterances** (from `adlc/agents/{agent-dev-name}__{org-alias}/baselines/{topic}/utterances.txt`) → regression tests
2. **Ticket attachments** → examples of bad/new behavior
3. **Derived from instruction + requirements** → edge cases, gaps

**Coverage check:** Every ticket requirement must have at least one test utterance — derive missing ones.

**Multi-turn awareness:** Classify each requirement as single-turn (first-response change) or multi-turn (follow-up behavior change, or naturally multi-step interaction like "select an item then explain it"). Use `conversationHistory` in the YAML spec for multi-turn tests.

**Guardrails:**
- Minimum 5 multi-turn test cases per ticket
- Maximum ~50 utterances per ticket. If the change needs more, return to Phase 2's risk-reduction gate to reconsider splitting before proceeding — don't re-derive the split decision here.

**Split eval criteria into three buckets:**
1. **Regression (unchanged)** — existing criteria that still apply as-is
2. **Regression (modified)** — existing criteria the ticket changes. These move to ticket eval AND update regression for QA.
3. **New ticket criteria** — entirely new metrics from requirements

Store regression spec and capability spec separately in `specs/`.

**Run the baseline now.** Use `testing-agentforce` to run the regression utterances against the live instruction and export results as CSV. Save it to the ticket folder as `baseline.csv` (Phase 3d analyzes this).

Record the Testing Center suite API name / eval definition name in `discovery.json` as `testing_center_suite_name` when Testing Center is used. If the baseline uses preview-only smoke instead, set this field to `null` and record the reason.

**3d. Analyze baseline and establish acceptance criteria:**

Before proposing criteria, analyze the baseline CSV to understand current metrics:
- Follow `adlc/playbooks/eval-report-playbook.md`, then run `python3 adlc/scripts/generate_report.py --prev <baseline.csv> --new <baseline.csv> --output /tmp/baseline-analysis.html` (comparing baseline to itself gives you the feature profile)
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
- 3a: Canonical metadata resolved, folder created, `discovery.json` written ✓
- 3b: Originals saved, conflicts audited, `discovery-context.md` written (mental model + dependency map) ✓
- 3c: Test specs built (utterances + coverage + multi-turn), baseline run, `baseline.csv` saved ✓
- 3d: Baseline analyzed, acceptance criteria proposed, `config.json` drafted ✓

**Then present to user and wait for approval. Group the checkpoint into 4 sections so the user can scan it:**

**1. Discovery findings** (from 3a + 3b)
- Instruction analysis per topic + conflicts found
- Prompt mental model summary (instruction edits only): structure, control flow, load-bearing scaffolding, insertion points, structure assessment
- Dependency map summary + per-requirement testability classification

**2. Test plan** (from 3c)
- Utterance counts, multi-turn count, coverage gaps mapped to requirements
- Baseline folder used and any mismatches reconciled

**3. Baseline + criteria** (from 3d)
- Baseline metrics (from fresh run, not stale data)
- Eval criteria split: unchanged / modified / new
- Proposed acceptance thresholds

**4. Exits + assumptions**
- Anything out of scope or deferred
- Assumptions and WHY

### Hand off to adlc-execute

**⛔ HARD GATE — do NOT skip this step.** Once the user approves Phase 3:

1. **STOP.** Do not continue planning, editing, authoring, or debugging inline.
2. **Log to HITL:** `{"phase":"3-handoff","type":"context","decision":"Entering Phase 4 via adlc-execute"}` — this creates an audit trail that the handoff happened.
3. **Read `~/.cursor/skills/adlc-execute/SKILL.md` NOW.** Do not proceed without reading it. Phase 4 starts inside that skill.

**⛔ Salesforce skills do NOT replace adlc-execute.** `developing-agentforce`, `observing-agentforce`, and `testing-agentforce` are execution tools that `adlc-execute` orchestrates during Phase 5 — not standalone phases. After any sub-skill call, return to `adlc-execute` for the test-evaluate-iterate loop and acceptance check. Going ad-hoc after a sub-skill call is the #1 process failure mode.

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
