# Multiplier Software Requests — Ticket Draft

**Status:** Draft (pre-JIRA). Move into the appropriate JIRA-keyed ticket folder under `adlc/agents/HelpIQ_AgentScript__aicommon/tickets/` once a key is assigned.
**Owner:** Oliver Guzman
**Executor:** `adlc-drive` (Phases 1–3) → `adlc-execute` (Phases 4–6). Human-in-the-loop is bounded to gate sign-off + architectural decisions explicitly marked **[HITL]**.
**Drafted:** 2026-05-13 (revised same day for eval rigor + adlc-drive consumption)
**Inputs:**
- `multiplier-current-state.md` (evidence brief — pre-ticket)
- `multiplier-discovery-transcript.md` (verbatim discovery, 2026-05-13)
- `~/HelpIQ-Evaluation/access-request-patterns-2026q1.md` (13 recs from 19 deep-read jira tickets)
- `~/HelpIQ-Evaluation/jira-audit-2026-0{1,2,3}/*-category-audit.csv` (~267k rows)
- `~/HelpIQ-Evaluation/evals/scenarios/SW-ACCESS-*.yaml` (4 multi-turn scenarios, no runner)

---

## For adlc-drive / adlc-execute

This ticket is sized for autonomous execution. The agent should:

1. **Skip Phase 1–2 re-discovery** — `multiplier-current-state.md` and `multiplier-discovery-transcript.md` are pre-existing discovery artifacts; consume them directly into Phase 3 outputs.
2. **Treat all `[HITL]` markers as required pause points.** Do not proceed past a `[HITL]` gate without explicit user approval. All other steps execute autonomously.
3. **Treat all rubric thresholds and Test Center metrics as programmatic gates.** Pass/fail is computed from outputs, not negotiated.
4. **Apply the Test Center stall policy** (see Operational Policies below) without escalating to user unless stall exceeds 4 hours total or recurs across stages.
5. **Persist all eval artifacts under the ticket's `eval/` subfolder** during execution; promote to canonical baselines path only at closeout.
6. **Emit a stage-gate report** at every gate transition with: rubric dimension scores, Test Center metric deltas, top-app coverage tally, leakage holdout delta, list of probes that failed, and a proposed disposition (proceed / iterate / escalate-HITL). Format is at the agent's discretion; consistency across stages is what matters.

### Target environment

- **Org:** `aicommon`
- **Agent label:** `HelpIQ-AgentScript` (current version: v4)
- **Sub-agent under modification:** `HelpIqAgentMultiplierSoftwareRequests`
- **Authoring bundle source:** `force-app/main/default/aiAuthoringBundles/HelpIQ_AgentScript/HelpIQ_AgentScript.agent`
- **Action / retrieval definitions:** `force-app/main/default/genAiFunctions/HelpIqAgentApplicationAccessDetails/` and `force-app/main/default/genAiFunctions/HelpIqAgentMultiplierSoftwareRequests/`
- **Version registry:** `adlc/agents/HelpIQ_AgentScript__aicommon/AGENT_VERSION_REGISTRY.md` — append a new row at every published version transition during this ticket.
- **Existing regression suite:** baseline Test Center suite from HELPEXP-274. The agent should locate it at session start (likely under `~/HelpIQ-Evaluation/` or in the prior ticket folder); if not found, request the path from the user before Stage 0.5.

---

## Title

**Phase HelpIQ Multiplier sub-agent into UGB + Service Strategy with reasoning-rubric eval (staged)**

---

## Context

The `HelpIqAgentMultiplierSoftwareRequests` sub-agent currently routes most software-access requests directly into ticket creation with minimal upstream discovery. Per the brief and the 2026-05-13 discovery session with Anthony, HelpIQ should mirror the JSM portal's pre-submission slot-filling behavior: identify the app, confirm whose access is being requested, capture license type when relevant, disambiguate similar product names, detect bulk requests, and only then file. Today most of that happens (or fails to happen) inside the ticket comment thread, after the user has already disengaged.

In Test Center bulk runs (HELPEXP-274 baseline, 999 utterances), `MultiplierSoftwareRequests` is the **highest-performing** topic on coherence (99%) and action_completion completeness (95%). Conciseness sits at 82%, completeness on multiplier rows at 85%. **The structural port must not regress those numbers.** The risk is real: structural prompt changes to the highest-performing topic can introduce regressions even when the changes are individually correct.

Discovery surfaced ~6 distinct behavior gaps with different evidence strength (see brief §3). The ticket is staged to de-risk the structural port and let evidence accumulate stage-by-stage.

This ticket also raises eval rigor materially over HELPEXP-274. HELPEXP-274 evaluated agent **outputs** (coherence/conciseness/completeness via LLM-as-judge). This ticket adds **reasoning-trajectory evaluation** — grading per turn whether the agent took the right steps to reduce ambiguity before retrieval, called the right tool with the right arguments, and ran the right follow-ups before submitting. The debug record introduced in HELPEXP-274 v4 is the input signal.

---

## What needs to change

### Strategic shape

1. **Port `UNDERSTAND → GATHER → BUILD` (UGB)** from General QnA into Multiplier, adapted for slot-filling rather than knowledge retrieval.
2. **Apply the Service Strategy taxonomy with the action-with-info-layer split** — for Multiplier this renders as **Clarify / Answer / Confirm / Submit / Escalate** (5 buckets, vs. content sub-agents' 3). Multiplier has both an info layer (`HelpIqAgentApplicationAccessDetails` retrieval can resolve questions without action — "Zoom basic is auto-provisioned, no ticket needed") and an action layer (`HelpIqAgentMultiplierSoftwareRequests` requires Confirm before Submit). Answer is distinct from Submit; Answer-vs-Submit classification is a load-bearing rubric check. See `prompt-engineering-playbook.md` → `Editing Patterns` → `Instruction Structure`.
3. **Adopt patterns from `access-request-patterns-2026q1.md`** §1–§5 (opener/closer, clarifying-question shape, scope clarification, disambiguation, alternative offers).
4. **Preserve the v4 baseline metrics** as a hard regression gate at every stage.
5. **Build reasoning-trajectory eval rigor as Stage 0** before any prompt edit — frequency analysis, rubric, judge, pre-change baseline.

### Stage 0 — Eval program build (pre-prompt-work, blocking)

Nothing in Stages 1–4 starts until Stage 0 completes.

**Stage 0.1 — Product frequency analysis.**
- Filter `jira-audit-2026-0{1,2,3}/*-category-audit.csv` to access-request rows (likely `human_request_type = "Request Access to Software"` or equivalent).
- Extract app names from `summary` and `human_subcategory` fields. Light NLP / regex acceptable; the goal is a frequency table, not a perfect canonical list.
- Output: `eval/app-frequency.csv` (under the ticket folder) with columns `app, ticket_count, pct_of_access_tickets, source_months`.
- Acceptance: top-20 apps identified by volume; long-tail count documented; ≥80% of access tickets covered by top-20 + long-tail rollup (no large "unparseable" residual).

**Stage 0.2 — Rubric specification.**
- Author `eval/RUBRIC.md` (under the ticket folder) documenting the per-turn reasoning rubric:

```
A. AMBIGUITY & REQUEST-TYPE DETECTION (binary per type, in UNDERSTAND phase)
   A.1 app_ambiguous flagged when present?              [pass/fail]
   A.2 beneficiary_ambiguous flagged when present?       [pass/fail]
   A.3 scope_ambiguous flagged when present?             [pass/fail]
   A.4 license_type_required flagged when applicable?    [pass/fail]
   A.5 request_type classified correctly                 [informational/action/escalation]
        (informational = user wants info, no action queued;
         action = user wants something filed/provisioned;
         escalation = user wants human / out-of-scope)

B. GATHER TIMING
   B.1 If any A.1–A.4 = ambiguous: was GATHER suppressed (Clarify first)? [pass/fail]
   B.2 If A.1–A.4 all unambiguous: was GATHER called?                     [pass/fail]
   B.3 GATHER called with correct app argument?                           [pass/fail]

C. KNOWLEDGE CORRECTNESS (when GATHER fired)
   C.1 Returned app matches user intent?                              [pass/fail]
   C.2 On multi-result, did agent disambiguate before BUILD?          [pass/fail]
   C.3 Was retrieved info actually used in BUILD
        (vs. agent ignoring data and templating from prompt)?         [pass/fail]

D. BUILD CORRECTNESS
   D.1 Service Strategy classification matches expected?
       [Clarify / Answer / Confirm / Submit / Escalate]
   D.2 Output shape matches strategy:
       - Clarify = single ?, ≤5 numbered options, no preamble re-quoting user.
       - Answer  = informational resolution grounded in retrieved data;
                    no action queued; optional follow-on offer ("want me to
                    file a ticket?") is allowed but not required.
       - Confirm = closed yes/no, includes complete slot summary
                    (app, beneficiary, license type if applicable, scope),
                    no new ambiguities introduced.
       - Submit  = action call with required slots filled +
                    completion message naming approver/owner if known.
       - Escalate= handoff with stated reason and downstream owner.    [pass/fail]
   D.3 Pre-Submit slot completeness: all required slots filled?         [pass/fail]
   D.4 Confirm-summary accuracy: slots in Confirm match what gets
        Submitted (no drift between Confirm and Submit args)?           [pass/fail]
   D.5 Answer-vs-Submit classification correct
        (did the agent file when it should have answered, or
         answer when it should have filed)?                             [pass/fail]

E. CONFIRMATION FLOW (turn-pair check, multi-turn only)
   E.1 Every Submit preceded by a Confirm in the prior turn(s)?         [pass/fail]
   E.2 If user said "no" / corrected at Confirm,
        did agent loop back to Clarify / re-Confirm
        rather than Submit anyway?                                      [pass/fail]
   E.3 If user said "yes" at Confirm, did Submit fire on next turn
        (no extra Clarify / no abandoned thread)?                       [pass/fail]
   E.4 Answer turns do NOT require Confirm
        (Answer → no-Confirm path is correct, not a violation).         [info only]
```

- Each rubric dimension gets ≥2 worked examples (one pass, one fail) with rationale.
- The rubric is the **single source of truth for stage gates** — no separate "80% pass" rate gates.

**Stage 0.3 — Judge build.**
- Implement a thin LLM-as-judge that takes `(user_turn, agent_debug_record, agent_output, expected_outcomes)` and returns a scored rubric.
- **Judge model: Claude (Anthropic family).** Different family from the agent (GPT-5.2) to mitigate same-family bias.
- Output: per-turn JSON scores; per-scenario aggregation.
- Spot-check requirement: 10% of judge decisions per stage gate must be human-reviewed for agreement; if disagreement >15%, recalibrate rubric or judge prompt.

**Stage 0.4 — Debug record permanence decision. [HITL-1]**
- **Default decision:** debug record stays in the prompt permanently. Post-process to strip from user-facing output; expose to eval pipeline as JSON.
- Rationale: rubric depends on it; removing at closeout would kill the eval mechanism.
- Alternative for user override: emit debug record only in a "test mode" prompt variant. Costs prompt-divergence between prod and test.
- **Agent action:** present the default + alternative to user; pause for explicit decision before proceeding to Stage 0.5.

**Stage 0.5 — Pre-change baseline.**
- Sample 30 utterances stratified per the sampling rule below. Author 2 multi-turn YAMLs (`SW-ACCESS-PROBE-01.yaml`, `SW-ACCESS-PROBE-02.yaml`) covering the most common access scenarios.
- Run all probes against the **current v4 prompt** (no changes) through the new judge.
- Capture rubric scores per dimension. This is the **baseline that every stage must beat.**
- Also walk the existing 4 SW-ACCESS YAMLs (`SW-ACCESS-01..04`) through the judge, captured as additional baseline.

**Stage 0.6 — Sampling rule (applies to all subsequent stages).**

Per-stage utterance set = ~30 single-turn + 1–3 multi-turn YAMLs, stratified:

| Stratum | Count | Source |
|---|---|---|
| Top-20 apps by frequency | ≥10 distinct apps, ≥1 utterance each | `app-frequency.csv` from Stage 0.1 |
| Patterns-doc highlights | 5–8 utterances covering specific behaviors the patterns sampled (Claude variants, Qualtrics, scope flip-flop, etc.) | `access-request-patterns-2026q1.md` §2–§5 |
| Long-tail | 5 utterances drawn from low-volume apps (≤10 tickets in the audit) | jira-audit raw rows |
| **Leakage holdout** | **~25% of total (~7–8 utterances)** | **Drawn from jira-audit raw rows ONLY. Author of these MUST NOT read the patterns-doc summary for these tickets. Surfaced only at the stage gate, not pre-seen by prompt author.** |

Multi-turn YAMLs use **scripted variations**: each user turn has 2–3 pre-authored alternative replies. Operator selects one at run time but cannot improvise. This kills the demand-characteristics problem from operator-as-judge.

**Stage 0 gate (must pass to start Stage 1):**
1. Frequency analysis complete; coverage ≥80% of access tickets.
2. Rubric doc reviewed and approved. **[HITL-2]** — user approves rubric dimensions, expected values, and worked examples before judge build.
3. Judge runs reproducibly. Validate by having the user manually grade ~10% of pilot judgments (a small batch surfaced to the user at [HITL-2]); if agreement <85%, agent recalibrates rubric or judge prompt and re-validates before proceeding.
4. v4 baseline captured for all rubric dimensions on probe set + existing YAMLs.
5. Sampling rule documented; first stage's utterance set drafted (holdout files stored in a separate path the prompt-edit step does not read).

### Stage 1 — Structural port + on-behalf-of detection

**Stage 1.0 — Inputs:** Validate on-behalf-of frequency in jira-audit (filter for requester ≠ recipient or comments with "for", "on behalf of", a different name). **[HITL-3]** — agent reports frequency; if <5% of access tickets, agent proposes staging swap (license-type forward into Stage 1) and pauses for user approval before proceeding.

**Prompt changes (assuming on-behalf-of frequency confirmed):**
- Rewrite Multiplier instructions into UGB phases:
  - **UNDERSTAND:** parse utterance; identify app (or note ambiguity); detect requester vs. beneficiary; classify request_type (informational / action / escalation); classify Service Strategy (Clarify / Answer / Confirm / Submit / Escalate); emit debug record with all flags.
  - **GATHER:** call `HelpIqAgentApplicationAccessDetails` when app is unambiguous AND retrieval is needed (informational requests AND action requests both gather; only ambiguous requests defer to Clarify).
  - **BUILD:** produce Clarify / Answer / Confirm / Submit / Escalate output per Service Strategy; emit debug record's BUILD section.
- Add an on-behalf-of slot in UNDERSTAND. If detected, GATHER must capture beneficiary identity before Confirm.
- Port the Clarify template from General QnA (single `?`, numbered options, ≤5 options).
- **Add the Answer path:** when retrieval resolves the user's question without requiring an action (e.g., app is auto-provisioned, user already has access, request is a policy question), produce an Answer turn grounded in retrieved data. May include optional follow-on offer ("want me to file a ticket?"). Answer turns do NOT require Confirm.
- **Add the Confirm step:** when request_type = action AND all required slots are filled (app, beneficiary, scope, license-type if applicable), the prompt must produce a Confirm turn — closed yes/no, slot summary surfaced — before Submit. Submit fires only after explicit user "yes" / equivalent. Per the playbook, zero-Confirm Submits are a failure mode for action sub-agents.
- Debug record block stays (decision per Stage 0.4); strip from user-facing output via post-processing.

**Out of Stage 1:** license-type, full disambiguation template, bulk, catalog miss, geo/role.

**Stage 1 gate (all must pass):**
1. **Regression (Test Center, blocking):** multiplier-row metrics on the existing regression suite (HELPEXP-274 baseline; agent locates at session start) within ±2 pts of v4 (coherence ≥97%, conciseness ≥80%, completeness ≥83%, action_completion completeness ≥93%).
2. **Rubric — UNDERSTAND dimension:** ≥30% relative improvement over v4 baseline on A.1 (app_ambiguous), A.2 (beneficiary_ambiguous), and A.5 (request_type classification) across the Stage 1 probe set.
3. **Rubric — GATHER dimension:** B.1 (suppress GATHER on ambiguity) and B.3 (correct app arg) at ≥85% absolute on the Stage 1 probe set.
4. **Rubric — BUILD dimension:** D.1 (Service Strategy classification across Clarify / Answer / Confirm / Submit / Escalate) at ≥85% absolute; D.2 (output shape) at ≥85% absolute; D.4 (Confirm-summary accuracy) at ≥85% absolute on probes that reach Confirm; **D.5 (Answer-vs-Submit classification) at ≥90% absolute** — wrong-direction errors (file when should have answered, or answer when should have filed) are high-impact production failures.
5. **Rubric — CONFIRMATION FLOW dimension:** E.1 (every Submit preceded by Confirm) at **100%** on the Stage 1 probe set. Zero-Confirm Submits are blocking. E.2 and E.3 at ≥85% absolute.
6. **Top-app coverage:** Stage 1 probe set touched ≥10 distinct top-20 apps.
7. **Leakage holdout:** holdout utterances scored after the prompt is locked for Stage 1; rubric scores within 10 pts of non-holdout. Larger gap = leakage suspected, debrief and recalibrate before Stage 2.
8. **No regression on existing 4 SW-ACCESS YAMLs** vs. their Stage 0.5 baseline judge scores.
9. **Multi-turn fixed:** new YAML `SW-ACCESS-05-on-behalf-of.yaml` (with scripted variations) — judge scores ≥85% on rubric dimensions A, B, D, E.

**Stage 1 sign-off: [HITL-4]** — agent emits stage-gate report; user reviews and approves proceed / iterate / abandon before Stage 2 starts.

### Stage 2 — License type + app disambiguation

**Prompt changes:**
- Add license-type slot for apps that require it (start list from `access-request-patterns-2026q1.md` §3 — Salesforce, Tableau; expand from Stage 0 frequency table for top-20 apps that have license tiers).
- Implement disambiguation template per patterns §2.5 — "name the ambiguity, offer reference link, ask closed question" — for Claude variants (claude.ai vs Claude Desktop vs Claude Code), Qualtrics instance, Gitlab/GitHub.
- GATHER phase: license-type prompt fires only when app is in the license-required list AND user has not already specified.

**Stage 2 gate:**
1. Stage 1 gates 1–5 all still pass on Stage 2's probe set (regression check is cumulative; Confirmation Flow gate carries forward).
2. **Rubric — A.4 (license_type_required):** ≥30% relative improvement over v4 baseline; ≥85% absolute on rubric.
3. **Rubric — C.2 (multi-result disambiguation):** ≥85% absolute.
4. **Rubric — D.4 (Confirm-summary accuracy with license-type slot):** ≥85% absolute on probes that reach Confirm with license-type filled.
5. **Top-app coverage:** Stage 2 probe set touched ≥10 distinct top-20 apps (may overlap with Stage 1).
6. **Leakage holdout:** within 10 pts of non-holdout.
7. **Multi-turn fixed:** new YAMLs `SW-ACCESS-06-license-type.yaml` and `SW-ACCESS-07-disambiguation.yaml` — judge scores ≥85% on rubric dimensions A, B, D, E.

**Stage 2 sign-off: [HITL-4]** — agent emits stage-gate report; user reviews and approves before Stage 3 starts.

### Stage 3 — Bulk + catalog miss

**Prompt changes:**
- Bulk detection: parse "for my team", "for X and Y", numeric counts. UNDERSTAND tags as bulk. GATHER asks for explicit list (patterns §2.4).
- Catalog miss → "Other" path: when app is not in the maintained catalog, route to a structured "Other" Submit with explicit free-text app name + use case.

**Stage 3 gate:**
1. Stages 1+2 gates still pass on Stage 3's probe set (Confirmation Flow gate carries forward).
2. **Rubric — A.3 (scope_ambiguous detection):** ≥30% relative improvement; ≥85% absolute.
3. **Rubric — D.3 (slot completeness on "Other" Submits):** ≥85% absolute on catalog-miss probes.
4. **Rubric — D.4 (Confirm-summary accuracy with bulk scope or "Other" app):** ≥85% absolute on probes that reach Confirm in those branches.
5. **Top-app coverage:** ≥10 distinct top-20 apps in probe set.
6. **Leakage holdout:** within 10 pts of non-holdout.
7. **Multi-turn fixed:** new YAML `SW-ACCESS-08-bulk-and-other.yaml` — judge scores ≥85% on rubric dimensions A, B, D, E.

**Stage 3 sign-off: [HITL-4]** — agent emits stage-gate report; user reviews and approves either Stage 4 entry or skip-to-closeout based on rubric residuals.

### Stage 4 — Optional: geo/role pre-screen

Run only if Stages 1–3 evals leave systematic gaps that map to geo or role-based access policy. Agent's [HITL-4] sign-off at end of Stage 3 includes a recommendation on whether to run Stage 4 (based on residual rubric scores). User decides.

### Closeout

**Closeout sign-off: [HITL-5]** — before promoting eval assets to canonical baselines path, agent presents closeout doc + rubric-delta table; user approves promotion and out-of-scope documentation completeness.

- Run full 999-utterance Test Center suite — confirm no broader-topic regression beyond multiplier.
- Walk all SW-ACCESS YAMLs (existing 4 + new 4) through judge — confirm cumulative pass.
- Promote new utterances + YAMLs from the ticket's `eval/` subfolder to `adlc/agents/HelpIQ_AgentScript__aicommon/baselines/HelpIqAgentMultiplierSoftwareRequests/`.
- Write closeout doc summarizing rubric improvement deltas per dimension, residual gaps, and recommended follow-up tickets.
- **Debug record stays in the prompt** (per Stage 0.4 decision). Post-processing layer responsible for stripping it from user-facing output is documented as an operational dependency.

---

## Acceptance criteria (consolidated)

### Hard gates (every stage)

1. **No regression below v4 baseline** on multiplier rows in the existing Test Center regression suite (coherence ≥97%, conciseness ≥80%, completeness ≥83%, action_completion completeness ≥93%). **Test Center policy: blocking** — Stage N+1 cannot start until Stage N's Test Center run completes and passes.
2. **Rubric improvement** on the stage's target dimensions: ≥30% relative improvement over v4 baseline (Stage 0.5).
3. **Rubric absolute floor** on stage-relevant dimensions: ≥85%.
4. **Confirmation Flow:** E.1 (every Submit preceded by Confirm) at **100%**. Zero-Confirm Submits are blocking at every stage. E.2 and E.3 at ≥85% absolute. Per the playbook, this is the user trust mechanism for action sub-agents and is non-negotiable.
5. **Top-app coverage** in probe set: ≥10 distinct top-20 apps.
6. **Leakage holdout** scores within 10 pts of non-holdout. Larger gap → recalibrate before next stage.
7. **No regression on existing SW-ACCESS YAMLs** vs. Stage 0.5 baseline judge scores.

### Strategy-shape compliance

Strategy-shape rules (Clarify shape, Answer shape, Confirm shape, Submit shape, Escalate shape, tone) are graded **inside the rubric** as part of D.2 — they are not separate spot-check gates. The judge prompt incorporates `access-request-patterns-2026q1.md` §1–§5 directly. Per-shape requirements:

- Clarify: exactly one `?`, ≤5 numbered options, no preamble re-quoting the user.
- Answer: grounded in retrieved data (no hallucination); informational only; optional follow-on offer allowed; no Confirm required.
- Confirm: closed yes/no, complete slot summary surfaced (app, beneficiary, license, scope), no new ambiguities introduced.
- Submit: named approver/owner when known; completion message follows action call.
- Escalate: redirect to right downstream owner; no SLA timing promises.
- Tone: warm-professional ceiling; no exclamations except at resolution; no apology inflation.

The agent must include these as worked examples in `RUBRIC.md` (Stage 0.2).

### Closeout

- Closeout doc with rubric-dimension delta table.
- New eval assets promoted to canonical baselines path.
- Debug record post-processing layer documented.

---

## Out of scope (with documentation requirement)

These were surfaced during discovery but are NOT being executed in this ticket. Each must be documented with a one-paragraph problem statement + recommended owner before this ticket closes. The agent creates `multiplier-out-of-scope.md` in the agent folder (`adlc/agents/HelpIQ_AgentScript__aicommon/`) as part of Stage 0.

| Issue | Why deferred | Recommended owner |
|---|---|---|
| Router miss / welcome-message fallback (~22%) | Cross-cutting platform issue | HelpIQ platform team |
| KB ingestion lag (~1 week sync) | Operational pipeline | Parth / Sidude per Anthony |
| Catalog source-of-truth drift | Structural — needs canonical software catalog from SW Ops before any prompt-side fix | Software / IT Operations |
| Multi-language support | Out of current scope; tracked in patterns §9 | Future ticket |
| Multi-turn deterministic runner (replacing `sf agent preview` walkthroughs) | Build cost outweighs current ticket value; scripted-variation YAMLs are sufficient for v1 | Future infrastructure ticket |

---

## References

- `adlc/agents/HelpIQ_AgentScript__aicommon/multiplier-current-state.md` (evidence brief)
- `adlc/agents/HelpIQ_AgentScript__aicommon/multiplier-discovery-transcript.md` (discovery transcript, 2026-05-13)
- `adlc/playbooks/prompt-engineering-playbook.md` (UGB + Service Strategy principles)
- `adlc/playbooks/ticket-prep-playbook.md` (this ticket's prep history)
- `adlc/docs/helpiq-generalqna-phased-reasoning-spec.md` (HELPEXP-274 reasoning spec — source of UGB pattern + debug record)
- `~/HelpIQ-Evaluation/access-request-patterns-2026q1.md` (specialist patterns synthesis)
- `~/HelpIQ-Evaluation/jira-audit-2026-0{1,2,3}/` (~267k rows of access tickets)
- `~/HelpIQ-Evaluation/evals/scenarios/SW-ACCESS-*.yaml` (existing multi-turn fixtures)
- HELPEXP-274 (sibling work — General QnA phased reasoning, completed)

---

## Operational policies (for adlc-drive)

### HITL anchors — required pause points

The agent MUST pause and obtain explicit user approval at each of the following:

| Anchor | When | What user decides |
|---|---|---|
| **[HITL-1]** Architectural decisions | Before Stage 0.4 | Debug record permanence (default: keep permanent + strip from user-facing output). Override option: test-mode-only emission. |
| **[HITL-2]** Rubric approval | After Stage 0.2 draft, before Stage 0.3 judge build | Confirm the rubric dimensions, expected values, and worked examples. |
| **[HITL-3]** Stage-order interpretation | After Stage 1.0 frequency analysis | If on-behalf-of <5% of access tickets, agent proposes staging swap; user approves or rejects. |
| **[HITL-4]** Stage gate sign-off | At each of Stage 1, 2, 3, (4) gates | User reviews the stage-gate report and approves proceed / iterate / abandon. |
| **[HITL-5]** Closeout | Before promoting eval assets to canonical baselines | User signs off on closeout doc and rubric-delta table. |
| **[HITL-stall]** Test Center stall escalation | If a Test Center run stalls >4 hours total OR stalls recur across stages | User decides: continue with rubric-only judgment, restart, or pause ticket. |

All other steps (frequency analysis, judge build, prompt edits, eval runs, doc generation, etc.) execute autonomously.

### Test Center stall policy

1. **Normal:** Test Center runs typically complete in ~7–15 minutes.
2. **Stall threshold:** if a run exceeds 1 hour with no progress, log as stalled and continue running; check every 30 min.
3. **Soft fallback (1–2 hour stall):** agent proceeds with rubric-only judgment for the current stage; marks Test Center regression gate as **"pending verification"**; continues to next stage's prompt work.
4. **Hard fallback (>4 hour stall OR recurrence):** **[HITL-stall]** — escalate to user.
5. Pending verification gates are resolved at the next successful Test Center run; if they fail at that point, all dependent stage work rolls back to the last known-good state.

### Review cadence

- Default: **per-stage review** at each of [HITL-4] anchors (~5 review touchpoints across the ticket).
- Per review: ~15–30 min of user time reviewing the agent's stage-gate report.
- Total user time across the ticket: ~2–3 hours of focused review + occasional [HITL-stall] response.
- If user prefers lower frequency, batch [HITL-4] approvals at Stage 2 and Closeout only — agent runs Stages 1 and 3 autonomously between reviews. **Default is per-stage review unless user opts otherwise at ticket kickoff.**

---

## Open questions / risks (for HITL)

1. **On-behalf-of frequency is anecdotal.** Stage 1.0 measures it. If <5% of access tickets, staging order swaps.
2. **Multiplier currently leads on coherence.** A poorly-executed structural port could regress it. Stage gate #1 (Test Center regression, blocking) is the primary safeguard.
3. **Debug record permanence is a real architectural commitment.** Default decision (Stage 0.4) is keep permanent + post-process to hide from user. Override option: emit only in test-mode prompt variant. **Decide before Stage 0.4 starts.**
4. **Rubric thresholds (≥30% relative improvement, ≥85% absolute) are picked, not derived.** No statistical basis. Adjust if v4 baseline shows extreme starting points (e.g., if v4 already hits 85% on a dimension, ≥30% relative improvement is unrealistic — switch to absolute floor only).
5. **Judge model choice (Claude for grading GPT-5.2 agent).** Right call for bias mitigation but introduces dependency on a second LLM. If Claude availability is constrained, alternative is `gpt-4o` or another OpenAI model that's not the agent's runtime model.
6. **Top-app frequency analysis quality depends on jira-audit field cleanness.** If `summary` and `human_subcategory` don't yield a parseable app name in ≥80% of rows, Stage 0.1 needs LLM-assisted extraction (cheap, but adds time).
7. **Leakage holdout discipline requires the prompt author NOT to read the patterns-doc summary for the holdout ticket keys.** This is operational — there's no technical enforcement. Document the discipline; honor it on trust.
8. **No multi-turn runner means each YAML walkthrough is operator time.** With scripted variations the operator's discretion is bounded but not zero. Planned mitigation: rubric judge scores the conversation transcript, not the operator's recollection.
9. **Stage 4's optionality is honest** but means the ticket may close without geo/role behavior addressed. If geo/role gaps surface in production post-closeout, they file as a follow-up ticket.
10. **Service Strategy asymmetry across sub-agents.** Multiplier has 5 buckets (Clarify / Answer / Confirm / Submit / Escalate); General QnA has 3 (Clarify / Answer / Escalate). The asymmetry reflects that action sub-agents with an info layer have both an informational resolution path (Answer) and an action path (Confirm + Submit). Documented in `prompt-engineering-playbook.md`. If a future sub-agent appears to need a sixth bucket, the playbook's discipline rule applies: only split when the rubric can't grade the unified bucket accurately.
11. **Answer-vs-Submit classification is the highest-impact rubric dimension.** Wrong-direction errors are real production failures (annoyed users from unnecessary tickets; missed access from incorrectly Answering). The 90% absolute floor on D.5 is intentionally higher than other dimensions. If v4 baseline shows this is already very high (likely — the current prompt over-Submits), the gate effectively measures whether we maintain Submit accuracy while adding Answer capability.
12. **Zero-Confirm Submits as blocking failure may have edge cases.** Reversible no-cost actions (e.g., a future "save draft" action) might justify skipping Confirm. None exist in Multiplier today. If/when they do, the exception must be documented per-action, not blanket-applied.
