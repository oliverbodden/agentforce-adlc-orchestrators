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

## 1. RULES (apply to all phases, including adlc-execute)

**⛔ TRANSPARENCY RULE: Commit to decisions in writing BEFORE acting on them.** For every significant decision (which phase to enter, which skill to call, what to change, what to test, whether to proceed or stop), write out:
1. What you decided
2. Why (your reasoning — not restating instructions, but explaining your logic)
3. What you're about to do next

This is visible to the user as you work. It serves two purposes: the user catches wrong assumptions in real time, and you can't contradict your own reasoning (if you wrote "ServiceStrategy = EXPLAIN" you can't then generate an ESCALATE response).

**⛔ CHECKPOINT RULE: Phases that need user approval MUST pause and wait.** Phases that are just showing work can continue. The per-phase instructions below specify which checkpoints pause and which are output-only.

**⛔ PROCESS FAILURE RECOVERY: When the user identifies a process failure, STOP all work.** Re-read the FULL requirements for the current phase. Audit every requirement against your actual actions — not just the one the user flagged. Log ALL gaps found to HITL. Only resume after the audit is logged and the user confirms.

**⛔ HITL LOG RULE: Append a JSONL entry to both files IMMEDIATELY after each of these events:**
- User responds to a checkpoint (type: approval/correction/rejection)
- User provides information (type: context)
- Agent generates significant analysis — triage, blast radius, test matrix, plan options, acceptance criteria (type: context)
- Process failure is identified (type: process-failure)
- Session ends early (type: early-exit)

Files:
1. `adlc/hitl/{ticket-key}.jsonl` (per-ticket audit trail)
2. `adlc/hitl/index.jsonl` (central rollup)

HITL is the single source of truth for the session — not chat, not separate files.

Entry format: `{"ts":"<ISO8601>","session_id":"<chat-id>","phase":"<N-name>","checkpoint":"<what>","type":"<approval|correction|rejection|context|escalation|early-exit|process-failure>","asked":"<what you presented>","decision":"<what user said>","agent":"<agent>","topic":"<topic>","ticket":"<key>","who":"<user>","org":"<org>","agent_version":"<version>","edit_strategy":"<strategy>"}`. Include `org`, `agent_version`, and `edit_strategy` from Phase 2 onward. See `adlc/hitl/README.md` for field definitions. Log the interaction as it happened — do not sanitize or summarize the user's words.

**Delegation map:**

| Capability | Delegated to |
|---|---|
| Evaluate ticket readiness, help write tickets | `adlc-ticket` |
| Read/edit topic instructions, trace analysis, agent improvement | `adlc-optimize` |
| Run tests, bulk evals, export results | `adlc-test` |
| Resolve agent/topic metadata in org | `adlc-discover` |
| Generate missing Flow/Apex stubs | `adlc-scaffold` |
| Build new agent or major rewrite | `adlc-author` |
| Plan, execute iterations, present results, hand off | `adlc-execute` |
| Deploy, publish, activate | `adlc-deploy` (user invokes separately) |

---

## 2. PHASES

### Phase 1: Goal

Capture what the user wants to achieve.

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

Create the ticket folder at `adlc/{agent-name}/tickets/{ticket-key}-{short-description}/` and document your understanding in `goal.md` inside it. Look for existing agent folders under `adlc/` to match the naming convention. ALL ticket artifacts go in this folder. I know you'll want to create it at the project root or in a `tickets/` shortcut — don't. Every artifact must live under `adlc/{agent}/tickets/` or it gets lost.

**⛔ CHECKPOINT (output only — no questions yet, no org queries):**
- Your understanding of the goal (in your own words)
- Ticket readiness assessment
- What you know vs what you still need to find out
- Any assumptions you're making and WHY

Then immediately proceed to Phase 2 — that's where questions happen.

### Phase 2: Refine

Collaborative back-and-forth to ensure alignment before any work starts.

**Before asking questions, read the architecture section of `adlc/prompt-engineering-playbook.md`.** Understand how the system works — topics, actions, instructions, templates, data flow — so your questions account for the full picture, not just the surface-level change.

**Then refine through conversation.** Based on your Phase 1 understanding, the ticket content, and the architecture, formulate questions that cover what you need to know to proceed. Don't use a fixed list — reason from context. I know you'll want to infer the agent name, version, org, and edit strategy from files like `agent-meta.json` — don't. Always ask the user explicitly. These are critical parameters that change between sessions and wrong assumptions here cascade through every subsequent phase.

**SPIKE gate:** At any point during refinement, if the problem or solution is unclear, propose a SPIKE — a time-boxed investigation that produces findings, not changes. If SPIKE, present the investigation plan and stop. Do not proceed to Phase 3.

**⛔ CHECKPOINT:** Present to user and wait for approval:
- Your understanding of the full scope (in your own words)
- What's in scope vs what you're explicitly NOT touching (and why)
- SPIKE gate decision (proceed or investigate)
- Any open questions or concerns
- Any assumptions and WHY

### Phase 3: Discover

Gather evidence about the current state. This is where the machine starts investigating — Phases 1-2 were human conversation only.

**3a-pre. Pull prior HITL history:**

Check `adlc/hitl/index.jsonl` for prior entries matching this agent and/or topic. Look for patterns: recurring corrections, prior rejections, known gotchas from earlier drives. Summarize relevant findings in the ticket's `goal.md` under a "Prior HITL context" heading. This informs your Phase 3 investigation and Phase 4 planning — don't repeat mistakes that were already caught.

**3a. Resolve agent/topic metadata:**

→ Read `~/.cursor/skills/adlc-discover/SKILL.md`
  You need: how to resolve agent and topic IDs for a Salesforce org (may or may not have an authoring bundle)
  Use the agent name and topics confirmed by the user in Phase 2.
  Store: agent_api_name, plugin_definition_id, instruction_def_ids, has_authoring_bundle

If discovery reveals surprises (more instruction records than expected, unexpected topic structure, agent version mismatch), HITL — present findings and re-confirm scope with user before continuing.

**3b. Pull current instructions + audit for conflicts:**

Use the agent/topic IDs resolved in step 3a.

**Save the original instruction text immediately** — before any analysis or editing. Store each instruction record as-is in the ticket folder:
```
adlc/{agent}/tickets/{key}/originals/
  {topic-name}-{record-id}.txt
```
These are the rollback point. Never modify the originals folder.

→ Read `~/.cursor/skills/adlc-optimize/SKILL.md`
  You need: how to read the current topic instruction from the org (for UI-built agents without authoring bundles, look for the Tooling API path)
  Execute those steps. Store: instruction text, word count for ALL affected instruction records (global + per-topic).

Then audit: do any existing instructions contradict the new guidelines? Flag conflicts (e.g., existing instruction says "use Here's what I found" but ticket says remove it). Document conflicts in goal.md.
  Then continue to 3c.

**3c. Establish baseline + build test utterances:**

Do NOT adopt pre-existing Testing Center test suites — build fresh from baseline utterances.

**Baseline utterances live in ONE place only:** `adlc/{agent}/baselines/{topic}/utterances.txt`
Do NOT search Downloads, project root, old ticket folders, or anywhere else for baseline data. If the utterance file doesn't exist for a topic, ask the user to provide one or derive utterances from the instruction.

**Baseline = utterances, not outputs.** I know you'll want to reuse an old CSV of outputs as the baseline to save time — don't. Org state changes between runs make old outputs invalid. Always run utterances against the live instruction to generate fresh outputs.

**Context variables check (HARD GATE):** Does this topic need session context (e.g., linked variables, account data, user identity) for testing? Ask the user — they know which topics need context vs which are self-contained. If context is needed, **STOP and ask the user what variables are required and their current values.** Do NOT proceed with testing if a topic needs context and you don't have it — results will be invalid. See playbook testing section for details.

**Combine ALL available sources for the test spec (AND, not OR):**
1. **Baseline utterances** (from `adlc/{agent}/baselines/{topic}/utterances.txt`) → regression tests
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

**Run the baseline now.** Invoke `adlc-test` to run the regression utterances against the live instruction and export results as CSV. This is the fresh baseline — save it to the ticket folder as `baseline.csv`. This CSV is what Phase 3d analyzes.

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

Document the criteria in the ticket folder's `config.json`.

**⚠️ HITL required** when existing eval criteria are being modified or flipped. The user must confirm that changing what "good" means was intentional — product or dev may not have reviewed the implications of flipping a metric.

**⛔ CHECKPOINT — do NOT present until ALL of the following are complete:**
- 3a: Metadata resolved ✓
- 3b: Instructions pulled, originals saved, analysis checklist done ✓
- 3c: Test specs built (utterances + coverage check + multi-turn) ✓
- 3d: Baseline run, metrics analyzed, acceptance criteria proposed ✓

**Then present to user and wait for approval:**
- Instruction analysis per topic (from checklist)
- Conflicts found
- Test specs built (utterance counts, multi-turn count, coverage gaps)
- Baseline metrics (from fresh run, not stale data)
- Eval criteria split: unchanged / modified / new
- Proposed acceptance thresholds
- Exit ramps (anything out of scope)
- Assumptions and WHY

### Hand off to adlc-execute

Once the user approves Phase 3, proceed:

→ Read `~/.cursor/skills/adlc-execute/SKILL.md`
  Continue with Phase 4 (Plan). All discovery artifacts, acceptance criteria, and conversation context carry forward.

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
