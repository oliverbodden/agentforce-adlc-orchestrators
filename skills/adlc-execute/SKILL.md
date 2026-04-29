---
name: adlc-execute
description: >-
  Plan and execute Agentforce agent instruction changes iteratively. Takes
  discovery artifacts from adlc-drive (Phase 3), plans the approach, runs
  the edit-test-evaluate loop, presents results, and handles hand off.
  Invoked by adlc-drive after discovery is complete, or directly when
  resuming a session that already completed Phases 1-3.
---

# ADLC Execute

Plan, execute, present, and hand off agent instruction changes.
This skill owns Phases 4-7. It assumes Phases 1-3 (Goal, Refine, Discover)
are complete — the conversation context contains the goal, scope, discovery
findings, acceptance criteria, and approved test specs.

The rules from `adlc-drive` Section 1 (Transparency, Checkpoints, HITL
Logging, Process Failure Recovery) apply here. If you haven't read them
in this session, read `~/.cursor/skills/adlc-drive/SKILL.md` Section 1 now.

Before planning or executing, also read the local overlay docs if they exist:

- `adlc/playbooks/agentforce-architecture-playbook.md`
- `adlc/docs/core-process-overlay.md`
- `adlc/docs/acceptance-eval-hitl-governance.md`

These docs define project-specific architecture diagnosis, Solution Strategy Review, testing separation, acceptance governance, HITL improvement signals, and artifact closeout. If they conflict with this skill, pause for HITL and follow the approved local overlay unless the user approves an exception.

---

## Phase 4: Plan

Based on discovery findings, produce the execution plan.

**First: Re-read `adlc/playbooks/agentforce-architecture-playbook.md`, `adlc/docs/core-process-overlay.md`, and the Quick Routing Index, Prompt Strategy, Diagnostics, and Editing Patterns sections of `adlc/playbooks/prompt-engineering-playbook.md` NOW using the Read tool.** Do not proceed from memory. Extract the architecture, strategy, and prompt principles that apply to THIS goal before planning.

**4-pre. Architecture review:**

Before triaging or generating plan options, determine the work type and what sub-skills Phase 5 will need. Review the Phase 3 discovery artifacts and answer:

1. **Work type:** Is this an instruction edit (modifying existing topic instructions), a new agent authoring (creating an agent via `.agent` file), a scaffold + edit (creating missing actions then editing instructions), or a combination?
2. **Handoff artifact:** Read the ticket folder's `discovery.json` if present. Use it to confirm `source_of_truth`, instruction record IDs, canonical ticket folder, baseline CSV, config path, and Testing Center suite name. If `discovery.json` is missing in a new run, reconstruct the same fields from `goal.md`, `hitl.jsonl`, `config.json`, and Phase 3 artifacts before planning; if any required field is ambiguous, STOP for HITL.
3. **Sub-skills needed:** Based on the work type, which skills will the CHANGE step in Phase 5 invoke? Map each planned change to a skill:
   - Instruction edits / optimization / trace-informed fixes → `observing-agentforce` plus the local UI-built exception path when Phase 3 set `source_of_truth=ui-built-tooling-api`
   - New agent, major rewrite, scaffold, deploy, publish, activate → `developing-agentforce`
   - Preview smoke, Testing Center batch testing, action execution → `testing-agentforce`
4. **Source-of-truth gate:** Confirm the Phase 3 `source_of_truth` value. If `authoring-bundle`, use Salesforce `.agent` validate/publish flow. If `ui-built-tooling-api`, read `adlc/docs/core-process-overlay.md` section "UI-Built Agent Exception Path" and use the local exception only for the approved instruction records. If `ambiguous`, STOP for HITL before planning edits.
5. **Iteration model:** For instruction edits, one iteration = one instruction change. For authoring, define what constitutes an iteration explicitly (e.g., "Iteration 1: generate .agent file. Iteration 2: publish and fix validation errors. Iteration 3: verify live actions with --use-live-actions. Iteration 4: run full eval."). Each iteration must be a single logical step with a testable outcome.
6. **Validation model:** For instruction edits, validation = smoke test utterances. For authoring, validation also includes publish success, action invocation (live, not mocked), and org metadata checks. Document what "passing" means for each iteration.
7. **Comparison model:** For instruction edits, comparison is same-agent before/after (baseline.csv vs new.csv). For authoring that replicates a source agent, comparison is cross-agent (source agent outputs vs new agent outputs for the same utterances). Document which model applies.

Log the architecture review to HITL. This review drives everything in Phase 5 — if it's wrong, the execution will be wrong.

**4-pre2. Solution Strategy Review:**

Before triage and plan options, use the Phase 3 dependency map and prompt mental model and answer:

1. Is the issue actually in instructions, or in routing, action selection, action execution, data/RAG, context, environment, or product definition?
2. Is the current topic/subagent the correct surface?
3. Does the ticket-requested approach conflict with architecture evidence?
4. Which 2-3 strategies are viable, and what are their trade-offs?
5. Which strategy is recommended and why?
6. What validation path proves the strategy worked?
7. Which requirements cannot be tested accurately in lower env?
8. If this is prompt-facing, is the prompt structure `targeted-edit-safe`, `messy-but-workable`, or `restructure-recommended`?

HITL is required if the recommendation contradicts the ticket, changes product behavior, changes eval criteria, touches routing, requires new action/topic/data work, uses Salesforce docs to change strategy, or accepts untestable residual risk.

Prompt restructure is not a default strategy. Recommend restructure only when Phase 3 evidence shows the prompt is clearly contradictory/messy, targeted edits are unsafe, or repeated approved iterations failed because prompt structure appears to be the blocker. If restructure is recommended, HITL is required and the plan must explain why a targeted edit is not sufficient.

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
- **Max iterations:** set explicitly based on scope (narrow: 3-5, moderate: 5-8, broad: 8-12)
- **Pass threshold:** default 90%, adjust per user's acceptance criteria

**4c. Generate plan options:**

For changes with multiple implementation approaches, generate 2-3 plan options with pros/cons/risks. Recommend one. If the change affects architecture, flag for HITL. If eval fails on one approach, try the next.

**⛔ CHECKPOINT:** Present to user and wait for approval:
- Solution Strategy Review: failure class, viable strategies, recommended strategy, and why
- Plan options (2-3 if multiple approaches exist) with pros/cons
- Recommended option and WHY
- Prompt strategy: prompt surface, prompt goal, structure assessment, targeted-edit vs restructure decision, and validation path
- Triage classification (ship it / proctor / design review)
- Execution order (which topics/changes first)
- Test matrix (utterance counts, multi-turn ratio, run count, pass threshold)
- Max iterations
- Rollback strategy
- Estimated instruction size change (% increase/decrease)
- Any risks or concerns

---

## Phase 5: Execute + Iterative Evaluate

The iterative loop. This is where the work happens. Phase 5 owns both execution and per-iteration evaluation; Phase 6 is the final evaluation presentation once a candidate is ready or the approved iteration budget is exhausted.

Autonomy rule: if a smoke test, bulk eval, or acceptance check fails for a diagnosable reason within the approved Phase 4 strategy and scope, diagnose and iterate without HITL. Stop for HITL only when the result is ambiguous, the fix would change scope/strategy/product behavior/eval criteria, a hard gate is reached, or max iterations are exhausted.

**Prompt diagnostic rule:** For prompt-facing work, if repeated edits fail and the failure layer is unclear, stop adding more prompt rules and switch to diagnosis. As a default trigger, after about 3 unsuccessful prompt iterations, evaluate whether temporary diagnostic logs are needed before continuing.

Diagnostic logs must be hypothesis-driven. State the suspected failure layer first, then add custom log fields that prove or disprove that hypothesis. Do not add a generic reasoning dump by default. Build the diagnostic template from the prompt mental model: routing/classification variables, tool-use decisions, tool input construction, retrieved data interpretation, strategy/template selection, response-construction checks, and final compliance checks.

For Agentforce, internal diagnostic logs may be suppressed by the trusted output layer. If hidden/internal logs are skipped or unavailable, ask HITL whether to enable a temporary user-facing diagnostic trace. To survive reliably, the trace may need layered reinforcement in all key output-control locations: top-level diagnostic/transparency requirement, post-tool final-response format, per-strategy or per-mode reminders, output rules, diagnostic template section, and final "required for every response / no exceptions" reminder.

The trace must use the same names and order as the prompt's own control variables where possible. Example: if the prompt uses `RequestType`, `ServiceStrategy`, `Goal addressed`, `Template`, and `Closing line`, log those exact fields. For prompts that do not use `UNDERSTAND / GATHER / BUILD`, mirror the actual architecture instead, such as `CLASSIFY / ROUTE / HANDOFF`, `QUERY / RETRIEVE / ANSWER`, or `INTENT / TOOL / RESPONSE`.

Treat exposed diagnostic traces as development scaffolding, not production output. Record diagnostic mode in `discovery.json`, and optionally mirror per-attempt details in attempt metadata, including the hypothesis, logged variables, insertion points, visibility, and removal requirements. Do not remove logs automatically while debugging unless the user approves productionization. Before final acceptance, remove or internalize the trace from every insertion point and compare behavior against the diagnostic version.

**Prompt reduction rule:** If diagnostic logs still do not reveal why a prompt-facing change is failing, or if the suspected blocker is a conflicting prompt layer, run a fast prompt-reduction loop before broad evals. Prompt reduction means temporarily removing, neutralizing, or simplifying one prompt layer at a time to discover whether the target behavior ever works and where it stops working. Use small preview/unit-style tests for this loop; do not use slow Testing Center regression as the primary isolation tool.

Prompt reduction must be staged and reversible: state the hypothesis, choose one section/layer to neutralize, save the modified attempt, run focused canaries, compare behavior, then restore or continue reducing based on evidence. Good reduction targets include duplicated output rules, late validation checks, action-output pass-through rules, prompt-template instructions, global-vs-topic conflicts, diagnostic scaffolding itself, and trusted-layer/output-contract wording. Stop for HITL if the reduction would change approved scope, remove load-bearing safety/escalation behavior, or leave the agent in a non-production-safe state beyond the diagnostic attempt.

**Loop structure:**

```
FOR each iteration (max N from Phase 4b):

  1. CHANGE — Execute the change defined by the Phase 4 plan for this iteration.
     - **Log to HITL:** "Entering Phase 5 iteration N, executing CHANGE using [skill] per Phase 4 plan." If the skill you're about to call doesn't match what Phase 4 planned, STOP — that's a process failure.
     - Re-read the Diagnostics, Editing Patterns, and Validation And Evaluation sections of adlc/playbooks/prompt-engineering-playbook.md NOW using the Read tool. Do not proceed from memory.
     - Refer to the goal and scope documented in goal.md

    **For instruction edits / optimization (observing-agentforce path):**
     - Make the targeted edit (reduce, modify, add, or restructure — whatever the goal requires)
     - If ADDING content: check % increase vs current instruction size. If exceeding playbook guidelines, pause and get user approval before proceeding.
     - If ADDING content: draft 2-3 variants of varying verbosity and placement. Present all variants to the user with pros/cons before deploying any.
     - Save new version to attempts/NN-name/instruction.txt
     - If `source_of_truth=authoring-bundle`: Read ~/.cursor/skills/observing-agentforce/SKILL.md and ~/.cursor/skills/developing-agentforce/SKILL.md. Edit the `.agent` source, validate, publish/activate through the authoring-bundle flow, and verify live behavior.
     - If `source_of_truth=ui-built-tooling-api`: Read `adlc/docs/core-process-overlay.md` section "UI-Built Agent Exception Path". PATCH only the approved instruction field on the approved `GenAiPluginInstructionDef` record, read it back, and record rollback metadata.
     - If source of truth is missing or ambiguous: STOP for HITL.
     - One change per iteration. When things break, you need to know which change caused it.

    **For new agent authoring / major rewrite (developing-agentforce path):**
     - Read ~/.cursor/skills/developing-agentforce/SKILL.md and execute the generation step.
     - Save the .agent file to the authoring bundle path.
     - Publish: run `sf agent publish authoring-bundle` and treat publish errors as iteration failures (back to step 1 with the fix, not ad-hoc debugging).
     - After publish succeeds, validate with `sf agent preview --authoring-bundle <name> --use-live-actions` — mocked actions do NOT count as validation. Confirm actions execute with real org data.
     - One logical step per iteration. For authoring, the iteration boundaries from Phase 4-pre apply.

    **For scaffold (developing-agentforce path):**
     - Read ~/.cursor/skills/developing-agentforce/SKILL.md and generate the missing stubs.
     - Deploy stubs to the org before proceeding to instruction edits or authoring that depend on them.

     The Phase 4 plan determines which path(s) you follow and in what order. Do not deviate.

  2. SMOKE TEST (quick, per-iteration)
     - 3-5 utterances, run each 4 times (3/4 pass = acceptable): at least 1 that exercises the change, at least 1 regression canary
     - Prefer `sf agent preview` (instant, no suite creation) for topics that don't need context variables
     - Use Testing Center only if context variables are required — reuse the same suite with `--force-overwrite`, don't create new ones
     - Goal: confirm the change didn't break the basic flow. Not comprehensive.

  3. EVALUATE
     - Pass rate >= threshold? → proceed to bulk eval
     - Pass rate < threshold? → diagnose, iterate (back to step 1)
     - If `diagnostic_mode` is active, do not fail the iteration solely because the approved diagnostic trace is visible. Treat visible traces as development scaffolding; final acceptance still requires removal/internalization or explicit product approval.
     - Ambiguous result, scope-changing fix, criteria-changing fix, or product trade-off? → PULL USER IN to confirm

  4. BULK EVAL (only when smoke tests pass)
     - Run full utterance set via Testing Center — reuse the suite created in Phase 3, `--force-overwrite` if spec changed
     - Compare: python3 adlc/scripts/generate_report.py --prev <baseline-csv> --new <new-csv> --output <report.html> --json-output <report.json>

  5. ACCEPTANCE CHECK
     - All blocking acceptance criteria for the current approved stage met? → EXIT loop, proceed to Phase 6
     - Deferred or future-stage criteria do not block this loop unless the run has been explicitly promoted to that stage.
     - Regression detected? → diagnose, iterate (back to step 1)
     - Regression fix would change approved scope/strategy/product behavior/eval criteria, or ambiguous? → PULL USER IN with data

  IF max iterations reached without meeting criteria:
     - STOP
     - Present what was achieved vs what was targeted
     - Ask user: continue with more iterations, adjust criteria, or abandon?
```

Salesforce skills are the source of truth for standard HOW. Execute decides WHAT and WHEN. Local overlay docs are the source of truth for project-specific exceptions such as UI-built Tooling API instruction edits and artifact/reporting conventions. When a step says to read a Salesforce skill or local overlay, read it, find the relevant section, execute, then return here.

**Checkpointing:**

After each iteration, save state so progress isn't lost if the session breaks:

Save resumability state to `.adlc-drive-state.json` in the project root. Include at minimum: goal, agent, org, current phase, iteration count, changes made so far, acceptance criteria summary, and status. Add whatever metrics are relevant for this specific goal — don't use a fixed schema. This file is a scratchpad for interruption recovery only. Durable handoff and audit state belongs in the ticket folder: `discovery.json` for source-of-truth/IDs/diagnostic mode, `config.json` for acceptance criteria and Phase 6 results, and `hitl.jsonl` for approvals and decisions.

Pull the user in when results are ambiguous, a fix would leave the approved scope or strategy, eval criteria/product behavior must change, a hard gate is reached, or you're stuck after 3 iterations. Do not interrupt for every ordinary regression if the cause is clear and the fix is within the approved plan.

---

## Phase 6: Present Final Evaluation

After acceptance criteria are met (or max iterations reached):

Before producing the final recommendation, read `adlc/docs/acceptance-eval-hitl-governance.md` if present. Final acceptance must combine automated eval evidence, product acceptance, technical/process review, environment/testability caveats, and HITL decisions.

1. **Generate the regression report:**
   ```bash
   python3 adlc/scripts/generate_report.py \
     --prev <baseline.csv> --new <final.csv> \
     --output <ticket-folder>/eval-report.html \
     --json-output <ticket-folder>/eval-report.json \
     --title "<goal summary>"
   ```

2. **Read the JSON output and produce the AI analysis layer.** The script handles metrics; you handle judgment. Read `eval-report.json` and cross-reference against the ticket's acceptance criteria from `config.json`:

   - **Scorecard interpretation:** Are the wins in areas the ticket targeted? Are regressions in areas the ticket didn't touch (unexpected) or expected trade-offs?
   - **Acceptance criteria check:** For each criterion in `config.json`, map it to specific metrics from the JSON. State pass/fail with evidence. Use `priority`, `tolerance_preset`, optional numeric thresholds such as `target`, `min_pass_rate`, or `max_regression_delta`, `blocking`, `status`, and `stage` to decide whether the result supports GO, CONDITIONAL, or NO-GO.
   - **Stage status:** If work is staged, separate current-stage acceptance from full-ticket completion. Deferred future-stage criteria are not failures when staging was approved and the deferred reason is recorded.
   - **Result recording:** Preserve `status` as the approval lifecycle (`approved`, `deferred`, `waived`, etc.). Write Phase 6 outcomes to each criterion's `result` object when updating `config.json`, with outcome, evidence, and short notes.
   - **Tool call accuracy** (if applicable): Compute from the raw CSV using the ticket's test spec annotations — which utterances should trigger which tools. The script doesn't do this; you do.
   - **Template adherence** (if applicable): Check topic-specific response patterns from the ticket spec against the raw responses.
   - **Diagnostic trace status** (if applicable): If `diagnostic_mode.used=true`, verify whether the trace was removed/internalized from every insertion point or explicitly approved by product to remain. Set `removal_verified=true` in `discovery.json` only after verification. Do not recommend final `GO` with unapproved exposed diagnostic traces.
   - **Regression explanation:** For each regression the scorecard flagged, explain whether it's blocking or acceptable and why. Reference the specific metric values.

3. **Propose playbook updates** — If new patterns were discovered during this ticket, propose additions to `adlc/playbooks/prompt-engineering-playbook.md`. User approves before changes are made.

4. Present a summary:

```markdown
## Drive Summary: <goal>

### Recommendation: [GO | NO-GO | CONDITIONAL]

### Executive Summary
<2-3 sentences: what changed, key wins, key risks. Written from the JSON scorecard data.>

### Changes Made
| # | Change | File/Topic | Iteration |
|---|--------|-----------|-----------|
| 1 | <what changed> | <where> | <which iteration> |

### Scorecard
<wins> wins | <regressions> regressions | <ties> ties

### Acceptance Criteria
| Criterion | Priority | Tolerance | Blocking? | Status | Evidence |
|---|---|---|---|---|---|
| <from config.json> | <critical/high/etc> | <exact/standard/etc> | <yes/no> | PASS/FAIL/DEFERRED/WAIVED | <metric name: baseline → new, delta> |

### Key Metrics
| Metric | Baseline | Final | Delta | Verdict |
|---|---|---|---|---|
[Pull from JSON — focus on metrics relevant to this goal, not all 35+]

### Regressions
| Metric | Baseline | Final | Delta | Blocking? | Explanation |
|---|---|---|---|---|---|
[Only regressions. State whether each is blocking or acceptable and why.]

### Remaining Risks
- <any known gaps or edge cases>

### Product Acceptance
- <representative scenarios reviewed, sign-off needed, or fast-lane rationale>

### Technical / Process Review
- <originals saved, scope respected, criteria unchanged or approved, coverage mapped, caveats documented>

### Diagnostic / Transparency
- <not used / removed and verified / internalized / product-approved exposed transparency remains>

### Environment / Testability
- <lower-env gaps, blocked scenarios, residual risk owner>

### Artifacts
- Instruction file: <path>
- Test suite: <name in org>
- Eval report (HTML): <path>
- Eval report (JSON): <path>
- Ticket folder: <path>
```

**⛔ CHECKPOINT:** Present to user and wait for approval:
- GO / NO-GO / CONDITIONAL recommendation and WHY
- All changes made (what was edited, in which instruction records)
- Acceptance criteria: pass/fail per criterion with evidence
- Scorecard summary + key metrics
- Product acceptance status
- Technical/process review status
- Diagnostic trace status: not used, removed/internalized, or product-approved exception
- Environment/testability caveats
- Each regression explained (blocking vs acceptable)
- Remaining risks or known gaps
- Proposed playbook updates (if new patterns discovered)

---

## Phase 7: Approval + Hand Off

Clean exit after the user reviews and approves the Phase 6 recommendation. Approval and handoff stay together: a final decision without artifact routing is incomplete, and artifact routing without approval is unsafe. Two paths depending on whether this goes to prod.

**7a. If deploying to prod (promote to baseline):**

The winning attempt becomes the new baseline. Baselines have two layers: **utterances** (`baselines/{topic}/utterances.txt`) are the permanent test inputs that persist across versions — Phase 7c manages those. **Version snapshots** (`baselines/v{N+1}/`) capture the instruction + eval results for a specific deployment — that's what 7a creates.

1. Ask user: "Attempt NN passed acceptance. Promote to baseline v[N+1]?"
2. If yes, copy the winning attempt's artifacts:
   ```
   adlc/agents/{agent-dev-name}__{org-alias}/baselines/v{N+1}/
     instruction-{topic}.txt    ← from attempts/NN/instruction.txt
     raw-outputs.csv            ← from attempts/NN/ (QA 8x run, not dev 4x)
     metadata.json              ← record: version, date, ticket, scoring version, org state
     eval-report.html           ← from attempts/NN/
   ```
3. The baseline raw-outputs.csv should be from a **QA-level eval (8x runs)**, not the dev smoke test. If only dev-level (4x) exists, run a QA eval before promoting.
4. Remind user to use `developing-agentforce` for the actual org deployment/publish/activation workflow.

**7b. If NOT deploying yet (keep in sandbox):**

- Roll back org to previous baseline instruction
- Leave the winning attempt in the ticket folder — it's ready for promotion later
- Note in `status.md` which attempt is the candidate

**7c. Update baseline utterances:**

Review if the ticket introduced behavior not covered by existing baseline utterances:
- Did this ticket add new capabilities that need new test utterances?
- Were new utterances created during Phase 3c (capability spec) that should become permanent?
- Did requirements change what "good" looks like, making some existing utterances obsolete?

If yes, propose additions/removals to the baseline utterance list (`adlc/agents/{agent-dev-name}__{org-alias}/baselines/{topic}/utterances.txt`). Get user approval before modifying.

**7d. Always:**

- Confirm the user has reviewed the Phase 6 summary
- If `diagnostic_mode.used=true`, confirm `removal_verified=true` or record explicit product approval for exposed transparency before production handoff
- Validate the artifact package: `goal.md`, `hitl.jsonl`, `discovery.json`, `config.json`, originals, specs, attempts, eval report JSON/HTML or a logged reason why unavailable, and `status.md` / final recommendation notes
- Route artifacts to the shared ADLC artifact repo, not the production agent repo, unless written governance says they are the same repo. Expected repo: `https://github.com/YOUR_ORG/YOUR_ADLC_ARTIFACT_REPO`
- Before guiding a push or PR, verify the current git remote. If it is not the shared ADLC artifact repo, stop and guide the user to clone/open the artifact repo separately.
- Each run writes to a unique ticket folder. Existing ticket folders are append-only unless the user explicitly confirms they are resuming that exact run.
- Do not overwrite rollup files manually unless the workflow explicitly assigns this run that role.
- If proctor was recommended, note the flag strategy
- If design review was tagged, note which items need sign-off
- Clean up `.adlc-drive-state.json` after durable ticket artifacts are current. Do not leave it as the audit trail; the audit trail is `hitl.jsonl` plus ticket artifacts.

**Do NOT auto-deploy.** Deployment is a separate decision with its own safety gates.
