---
name: adlc-drive
description: >-
  Goal-driven Agentforce agent improvement. Takes a goal or requirement,
  refines it collaboratively, discovers baseline state, plans and triages
  the work (proctor/design review/SPIKE/ship-it), executes changes via
  other ADLC skills, iterates until acceptance criteria are met, and
  presents results. Use when the user has a goal, improvement, bug fix,
  or feature request for an Agentforce agent.
---

# ADLC Drive

Orchestrate goal-driven agent improvements end-to-end: from intake through
execution to verified results. This skill owns the *what* and *why*; it
delegates the *how* to other ADLC skills (`adlc-optimize`, `adlc-test`,
`adlc-author`, `adlc-scaffold`, `adlc-discover`).

---

## 1. ROLE

Drive is the **brain**, not the hands. It:
- Tracks the goal and acceptance criteria across the entire session
- Decides which skill to invoke and when
- Evaluates results against criteria after each iteration
- Pulls the user in when decisions are ambiguous
- Stops when done (or when stuck)

**⛔ TRANSPARENCY RULE: Commit to decisions in writing BEFORE acting on them.** For every significant decision (which phase to enter, which skill to call, what to change, what to test, whether to proceed or stop), write out:
1. What you decided
2. Why (your reasoning — not restating instructions, but explaining your logic)
3. What you're about to do next

This is visible to the user as you work. It serves two purposes: the user catches wrong assumptions in real time, and you can't contradict your own reasoning (if you wrote "ServiceStrategy = EXPLAIN" you can't then generate an ESCALATE response).

**⛔ CHECKPOINT RULE: Phases that need user approval MUST pause and wait.** Phases that are just showing work can continue. The per-phase instructions below specify which checkpoints pause and which are output-only.

**Delegation map:**

| Capability | Delegated to |
|---|---|
| Evaluate ticket readiness, help write tickets | `adlc-ticket` |
| Read/edit topic instructions, trace analysis, agent improvement | `adlc-optimize` |
| Run tests, bulk evals, export results | `adlc-test` |
| Resolve agent/topic metadata in org | `adlc-discover` |
| Generate missing Flow/Apex stubs | `adlc-scaffold` |
| Build new agent or major rewrite | `adlc-author` |
| Deploy, publish, activate | `adlc-deploy` (user invokes separately) |

---

## 2. PHASES

### Phase 1: Goal

Capture what the user wants to achieve.

**Input:** One of:
- JIRA ticket key/URL → auto-pull goal, requirements, attachments (see Section 4)
- Open text → user describes the goal directly

If no ticket, ask the user to describe the goal in detail. Read the ticket or description and formulate your own understanding — different tickets need different questions.

**1b2. Evaluate ticket readiness:**

→ Read `~/.cursor/skills/adlc-ticket/SKILL.md`
  You need: evaluate if this ticket has enough context for drive to execute
  Execute the assessment. If verdict is "Not ready" or "Out of scope", stop and tell the user.
  If "Needs improvement", present gaps and ask user to fill them before proceeding.
  If "Ready" or "Ready with gap", continue.

Create the ticket folder at `evals/{agent-name}/tickets/{ticket-key}-{short-description}/` and document your understanding in `goal.md` inside it. Look for existing agent folders under `evals/` to match the naming convention. ALL ticket artifacts go in this folder — never create ticket folders at the project root or anywhere else.

**⛔ CHECKPOINT (output only — no questions yet, no org queries):**
- Your understanding of the goal (in your own words)
- Ticket readiness assessment
- What you know vs what you still need to find out
- Any assumptions you're making and WHY

Then immediately proceed to Phase 2 — that's where questions happen.

### Phase 2: Refine

Collaborative back-and-forth to ensure alignment before any work starts.

**Before asking questions, read the architecture section of `evals/prompt-engineering-playbook.md`.** Understand how the system works — topics, actions, instructions, templates, data flow — so your questions account for the full picture, not just the surface-level change.

**Then refine through conversation.** Based on your Phase 1 understanding, the ticket content, and the architecture, formulate questions that cover what you need to know to proceed. Don't use a fixed list — reason from context.

**SPIKE gate:** At any point during refinement, if the problem or solution is unclear, propose a SPIKE — a time-boxed investigation that produces findings, not changes. If SPIKE, present the investigation plan and stop. Do not proceed to Phase 3.

**⛔ CHECKPOINT:** Present to user and wait for approval:
- Your understanding of the full scope (in your own words)
- What's in scope vs what you're explicitly NOT touching (and why)
- SPIKE gate decision (proceed or investigate)
- Any open questions or concerns
- Any assumptions and WHY

### Phase 3: Discover

Gather evidence about the current state. This is where the machine starts investigating — Phases 1-2 were human conversation only.

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
evals/{agent}/tickets/{key}/originals/
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

**Baseline utterances live in ONE place only:** `evals/{agent}/baselines/{topic}/utterances.txt`
Do NOT search Downloads, project root, old ticket folders, or anywhere else for baseline data. If the utterance file doesn't exist for a topic, ask the user to provide one or derive utterances from the instruction.

**Baseline = utterances, not outputs.** Always run utterances against the live instruction to generate fresh outputs. Never reuse old output CSVs as baselines — org state changes make them invalid.

**Context variables check (HARD GATE):** Does this topic need session context (e.g., linked variables, account data, user identity) for testing? Ask the user — they know which topics need context vs which are self-contained. If context is needed, **STOP and ask the user what variables are required and their current values.** Do NOT proceed with testing if a topic needs context and you don't have it — results will be invalid. See playbook testing section for details.

**Combine ALL available sources for the test spec (AND, not OR):**
1. **Baseline utterances** (from `baselines/{topic}/utterances.txt`) → regression tests
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

**3d. Analyze baseline and establish acceptance criteria:**

Before proposing criteria, analyze the baseline CSV to understand current metrics:
- Run `python3 evals/scripts/generate_report.py --prev <baseline.csv> --new <baseline.csv> --output /tmp/baseline-analysis.html` (comparing baseline to itself gives you the feature profile)
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

### Phase 4: Plan

Based on discovery findings, produce the execution plan.

**4a. Triage classification:**

| Gate | Question | Outcome |
|---|---|---|
| Design review | Does this change what users see or how they interact? | Tag for **DESIGN REVIEW** (parallel — doesn't block execution planning) |
| Risk score | See blast radius scoring below | **SHIP IT** (0) / **JUDGMENT CALL** (1) / **PROCTOR** (2+) |

**Blast radius scoring (1 point each):**

- Touches more than one topic?
- Affects >10% of sessions (estimate from baseline data)?
- Hard to roll back?
- Touches PII, auth, payment, or escalation flows?
- Changes system-level instructions (affects all topics)?

| Score | Verdict |
|---|---|
| 0 | **SHIP IT** |
| 1 | **JUDGMENT CALL** — default to proctor if unsure |
| 2+ | **PROCTOR** — feature flag, gradual ramp |

**4b. Determine test matrix:**

Scale testing to the change scope. These are starting guidelines — adjust based on the topic's complexity and the user's requirements:
- **Narrow change** (single instruction edit): ~5 smoke tests, 3 scenarios
- **Moderate change** (new behavior or multi-section edit): ~10 tests, 5 scenarios
- **Broad change** (system-level or multi-topic): ~15 tests, 7 scenarios
- **Pass threshold:** default 90%, adjust per user's acceptance criteria

**4c. Generate plan options:**

For changes with multiple implementation approaches, generate 2-3 plan options with pros/cons/risks. Recommend one. If the change affects architecture, flag for HITL. If eval fails on one approach, try the next.

**⛔ CHECKPOINT:** Present to user and wait for approval:
- Plan options (2-3 if multiple approaches exist) with pros/cons
- Recommended option and WHY
- Triage classification (ship it / proctor / design review)
- Execution order (which topics/changes first)
- Test matrix (utterance counts, multi-turn ratio, run count, pass threshold)
- Rollback strategy
- Estimated instruction size change (% increase/decrease)
- Any risks or concerns

### Phase 5: Execute

The iterative loop. This is where the work happens.

**Loop structure:**

```
FOR each iteration (max N per Phase 4b):

  1. CHANGE — Edit instruction based on the goal
     - Consult evals/prompt-engineering-playbook.md for editing principles and rule levels
     - Refer to the goal and scope documented in goal.md
     - Make the targeted edit (reduce, modify, add, or restructure — whatever the goal requires)
     - If ADDING content: check % increase vs current instruction size. If exceeding playbook guidelines, pause and get user approval before proceeding.
     - Save new version to attempts/NN-name/instruction.txt
     - Deploy: Read ~/.cursor/skills/adlc-optimize/SKILL.md
       You need: how to deploy an updated instruction to the org (Tooling API for UI-built agents)
       Execute those steps.
     - One change per iteration (don't batch multiple changes)

  2. SMOKE TEST
     - Read ~/.cursor/skills/adlc-test/SKILL.md
       You need: how to create a YAML spec, run a Testing Center suite, and export results to CSV
       Use a small spec (5 utterances). Execute, store CSV.

  3. EVALUATE
     - Pass rate >= threshold? → proceed to bulk eval
     - Pass rate < threshold? → diagnose, iterate (back to step 1)
     - Ambiguous result? → PULL USER IN to confirm

  4. BULK EVAL (only when smoke tests pass)
     - Read ~/.cursor/skills/adlc-test/SKILL.md
       You need: run full Testing Center suite (all utterances), export CSV
       Execute, store CSV.
     - Compare: python3 evals/scripts/generate_report.py --prev <baseline-csv> --new <new-csv> --output <report.html>

  5. ACCEPTANCE CHECK
     - All acceptance criteria met? → EXIT loop, proceed to Phase 6
     - Regression detected? → diagnose, iterate (back to step 1)
     - Ambiguous? → PULL USER IN with data

  IF max iterations reached without meeting criteria:
     - STOP
     - Present what was achieved vs what was targeted
     - Ask user: continue with more iterations, adjust criteria, or abandon?
```

Sub-skills are the source of truth for HOW. Drive decides WHAT and WHEN. When a step says "Read adlc-X/SKILL.md", read it, find the relevant section, execute, return here. Consult `evals/prompt-engineering-playbook.md` before editing instructions.

**Checkpointing:**

After each iteration, save state so progress isn't lost if the session breaks:

Save state to `.adlc-drive-state.json` in the project root. Include at minimum: goal, agent, org, current phase, iteration count, changes made so far, acceptance criteria, and status. Add whatever metrics are relevant for this specific goal — don't use a fixed schema.

Pull the user in when results are ambiguous, regressions appear, or you're stuck after 3 iterations.

### Phase 6: Present

After acceptance criteria are met (or max iterations reached):

1. **Propose playbook updates** — If new patterns were discovered during this ticket, propose additions to `evals/prompt-engineering-playbook.md`. User approves before changes are made.
2. Present a summary:

```markdown
## Drive Summary: <goal>

### Result: [ACHIEVED | PARTIALLY ACHIEVED | NOT ACHIEVED]

### Changes Made
| # | Change | File/Topic | Iteration |
|---|--------|-----------|-----------|
| 1 | <what changed> | <where> | <which iteration> |

### Test Results
| Metric | Baseline | Final | Delta |
|---|---|---|---|
[Include whatever metrics are relevant for this goal — discovered during Phase 3e]

### Remaining Risks
- <any known gaps or edge cases>

### Recommendation
- [ ] Ready to deploy (invoke `adlc-deploy`)
- [ ] Needs design review on: <items>
- [ ] Deploy behind proctor — flag: <name>, ramp: <plan>

### Artifacts
- Instruction file: <path>
- Test suite: <name in org>
- Eval report: <path to HTML>
- Ticket folder: <path>
```

**⛔ CHECKPOINT:** Present to user and wait for approval:
- All changes made (what was edited, in which instruction records)
- Test results: baseline vs final for each metric
- Metrics that improved, held, or regressed
- Whether acceptance criteria were met (per criterion)
- Remaining risks or known gaps
- Recommendation (deploy / proctor / hold / needs more work) and WHY
- Proposed playbook updates (if new patterns discovered)

### Phase 7: Hand Off

Clean exit. Two paths depending on whether this goes to prod.

**7a. If deploying to prod (promote to baseline):**

The winning attempt becomes the new baseline. This is the ONLY way baselines are created.

1. Ask user: "Attempt NN passed acceptance. Promote to baseline v[N+1]?"
2. If yes, copy the winning attempt's artifacts:
   ```
   evals/{agent}/baselines/v{N+1}/
     instruction-{topic}.txt    ← from attempts/NN/instruction.txt
     raw-outputs.csv            ← from attempts/NN/ (QA 8x run, not dev 4x)
     metadata.json              ← record: version, date, ticket, scoring version, org state
     eval-report.html           ← from attempts/NN/
   ```
3. The baseline raw-outputs.csv should be from a **QA-level eval (8x runs)**, not the dev smoke test. If only dev-level (4x) exists, run a QA eval before promoting.
4. Remind user to invoke `adlc-deploy` for the actual org deployment.

**7b. If NOT deploying yet (keep in sandbox):**

- Roll back org to previous baseline instruction
- Leave the winning attempt in the ticket folder — it's ready for promotion later
- Note in STATUS.md which attempt is the candidate

**7c. Update baseline utterances:**

Review if the ticket introduced behavior not covered by existing baseline utterances:
- Did this ticket add new capabilities that need new test utterances?
- Were new utterances created during Phase 3d (capability spec) that should become permanent?
- Did requirements change what "good" looks like, making some existing utterances obsolete?

If yes, propose additions/removals to the baseline utterance list (`evals/{agent}/baselines/{topic}/utterances.txt`). Get user approval before modifying.

**7d. Always:**

- Confirm the user has reviewed the Phase 6 summary
- If proctor was recommended, note the flag strategy
- If design review was tagged, note which items need sign-off
- Clean up `.adlc-drive-state.json` (or leave as audit trail)

**Do NOT auto-deploy.** Deployment is a separate decision with its own safety gates.

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
