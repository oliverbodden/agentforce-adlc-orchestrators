# Acceptance, Eval, And HITL Governance

Local project governance for Agentforce ADLC runs. This document defines how final recommendations, product acceptance, technical review, eval reports, HITL logs, and monthly skill-improvement signals should work.

This is an overlay document. It does not modify Salesforce upstream standard skills.

---

## Acceptance Model

Every completed run should end with one of four statuses:

| Status | Meaning |
|---|---|
| `GO` | Ticket goal met, unchanged behavior protected, known risks acceptable. |
| `NO-GO` | Ticket goal not met, regression is unacceptable, or validation is insufficient. |
| `CONDITIONAL` | Change may proceed only with named follow-up validation, sign-off, or remediation. |
| `ABANDONED` | Work stopped because the goal was invalid, superseded, blocked, or out of scope. |

Acceptance must combine:

- Automated eval evidence.
- Product acceptance review.
- Technical/process review.
- Environment/testability caveats.
- HITL decisions and approvals.

Pass rate alone is not acceptance. A run can have strong automated metrics and still be `NO-GO` if product behavior, safety, routing, data, or testability risk is unresolved.

---

## Product Acceptance

Product acceptance answers whether the agent behavior is correct for the business, not merely whether an evaluator script scored it.

Review representative examples for:

- User intent alignment.
- Business-rule correctness.
- Tone, brand fit, and clarity.
- Escalation and handoff behavior.
- Refusal/scope behavior.
- Safety, auth, PII, payment, and policy-sensitive behavior.
- Multi-turn continuity and recovery.
- Whether changed behavior matches the ticket's intent.

Hard gate product review when:

- Product behavior changes.
- Escalation, refusal, safety, auth, payment, PII, or routing changes.
- Existing eval criteria are flipped, relaxed, or reinterpreted.
- A live scenario simulation disagrees with static eval results.
- The recommended implementation differs from the ticket-requested approach.

Fast lane is allowed when the work is a narrow instruction fix with a single affected topic, no routing/action/data changes, clear rollback, baseline evidence, and minimum before/after tests.

---

## Technical And Process Review

Technical/process review verifies that the ADLC run itself was trustworthy.

Required checks:

- Original instructions/configuration were saved before edits.
- Scope stayed within the approved topic/action/data boundaries.
- Strategy matched the discovered root cause.
- Prompt edits were not used to hide action, data, routing, permission, or environment failures.
- Eval criteria were not silently weakened.
- Requirements map to test cases or documented exclusions.
- Baseline and final runs are comparable or caveats are explicit.
- Context variables, routable IDs, tokens, permissions, and data setup are documented.
- Regressions were triaged against baseline behavior before being fixed or dismissed.
- HITL entries exist for hard gates, deviations, strategy changes, and residual risk.
- Artifact package is sufficient for another reviewer or monthly AI review to reconstruct decisions.

Technical/process review should produce a short final note:

```json
{
  "technical_review_status": "pass|pass_with_caveats|fail",
  "process_deviations": [],
  "unresolved_risks": [],
  "required_followups": []
}
```

---

## Eval Governance Layers

Keep eval layers separate so one score cannot hide a regression or weak ticket validation.

| Layer | Purpose | Governance |
|---|---|---|
| Fixed regression suite | Protect unchanged behavior | Hard to modify within a ticket. |
| Modified regression criteria | Track intentional changes to what "good" means | Requires HITL approval before baseline comparison. |
| New feature eval | Validate ticket-specific new or changed behavior | Must map directly to requirements/AC. |
| Scenario/product acceptance | Review realistic conversations and business correctness | May include qualitative review and live simulation. |
| Eval script changes | Change scoring/evaluator behavior | Must be gated separately from implementation changes. |

Changing implementation and evaluator logic in the same ticket is risky. It is allowed only with explicit HITL approval, a rationale, and a report section separating behavior changes from evaluator changes.

---

## Apples-To-Apples Eval Report

Every final eval report must compare baseline versus final. A final-only report is not sufficient for `GO`.

Comparable runs should use:

- Same test population.
- Same scenario definitions.
- Same context variables and routable IDs when applicable.
- Same Testing Center/static `conversationHistory` representation.
- Same run count target.
- Same scoring logic unless a criteria change was approved.
- Same lower environment, org, agent version, and authoring/deployed state where possible.

If cases are added, removed, skipped, changed, or non-comparable, the report must split:

- Comparable metrics.
- Newly added coverage.
- Skipped or blocked coverage.
- Changed criteria.
- Non-comparable caveats.

Minimum report sections:

| Section | Required content |
|---|---|
| `recommendation` | `GO`, `NO-GO`, `CONDITIONAL`, or `ABANDONED`, with rationale. |
| `summary_metrics` | Pass rate, wins/regressions/ties, routing accuracy, action accuracy, response quality, latency if available, multi-turn stability. |
| `regression_results` | Whether unchanged behavior held against stored baseline utterances and stable scenario set. |
| `ticket_goal_results` | Whether ticket requirements and acceptance criteria passed. |
| `scenario_results` | Static multi-turn and live simulation results separated. |
| `coverage_map` | Requirement-to-utterance/scenario mapping and coverage gaps. |
| `comparability` | Context, data, run count, evaluator, org, or scenario differences. |
| `environment_testability` | Lower-env limitations, missing prod dependencies, required tokens/context, untested scenarios, residual risk. |
| `product_acceptance` | Product review status and representative example references. |
| `technical_review` | Process review status, deviations, and follow-ups. |
| `hitl_summary` | Decisions, approvals, strategy changes, and improvement signals. |

For large runs, such as 500-case suites, do not collapse everything into one score. The report should show the full score and the meaningful slices: affected topic, adjacent topics, feature suite, static multi-turn, live simulation, and blocked/untestable cases.

---

## Environment And Testability Reporting

Discovery and eval reports must capture environment/testability limits instead of hiding them in notes.

Use these classifications:

- `fully-testable-lower-env`
- `partially-testable-lower-env`
- `requires-prod-like-data`
- `requires-token-or-context`
- `requires-external-system`
- `not-lower-env-testable`

Required fields per blocked or caveated requirement:

```json
{
  "requirement_id": "<id-or-short-name>",
  "classification": "requires-token-or-context",
  "why": "<specific blocker or mismatch>",
  "needed_to_test": ["<token/context/data/permission/system>"],
  "next_best_validation": "Testing Center with fresh RoutableId|live proctor|STDM trace review|product sign-off|technical sign-off",
  "included_in_go_no_go": false,
  "residual_risk_owner": "product|technical|operations|unknown"
}
```

Rules:

- Do not mark lower-env untestable scenarios as passed.
- Ask for required tokens, routable IDs, context variables, sandbox data, or permissions before running dependent tests.
- If a required context value expires, record the expiration as a comparability caveat.
- If production data or integrations are required, propose a controlled validation path rather than prompt workarounds.
- If residual risk is accepted, log who accepted it and why.

---

## HITL Log Strategy

HITL is both an audit trail and a monthly skill-optimization signal. Keep it structured enough for AI review across hundreds of tickets, but avoid logging routine noise.

Log HITL when:

- A hard gate is reached.
- The strategy changes.
- The recommendation contradicts the ticket.
- Eval criteria change.
- Product behavior changes.
- Lower-env cannot validate a critical scenario.
- A process deviation occurs.
- Salesforce docs or live org evidence changes the recommended path.
- A user correction reveals a skill flaw.
- Residual risk is accepted.

Do not log:

- Routine file reads.
- Routine tool calls.
- Repeated progress updates.
- Raw transcript dumps.
- Secrets, auth tokens, raw PII, or full customer transcripts unless governance explicitly allows it.

Minimum HITL entry:

```json
{
  "timestamp": "YYYY-MM-DDTHH:MM:SSZ",
  "ticket": "<ticket-or-NOTICKET>",
  "agent": "<agent>",
  "phase": "<phase>",
  "category": "normal-approval|skill-flaw|ticket-gap|platform-limitation|product-decision|process-deviation|environment-gap|strategy-change|criteria-change|risk-acceptance",
  "decision": "<what was decided>",
  "why": "<short rationale>",
  "evidence_refs": ["<path-or-url>"],
  "tradeoff": "<cost/risk accepted>",
  "approved_by": "<user-or-role>",
  "next_step": "<next action>",
  "improvement_signal": false
}
```

Skill-improvement fields are required when `improvement_signal` is `true`:

```json
{
  "improvement_signal": true,
  "signal_type": "skill-flaw|local-overlay-flaw|upstream-standard-gap|upstream-conflict|installation-drift",
  "skill": "adlc-drive|adlc-execute|adlc-ticket|developing-agentforce|testing-agentforce|observing-agentforce|overlay-docs|bootstrap",
  "phase": "<phase-or-step>",
  "failure_mode": "<short_snake_case>",
  "severity": "low|medium|high|critical",
  "suggested_skill_update": "<specific proposed update>",
  "source": "trace|eval|user-correction|salesforce-doc|reviewer|artifact-review",
  "source_ref": "<path-or-url-or-ticket-artifact>"
}
```

---

## Monthly Skill-Improvement Review

Monthly AI review should operate on raw, machine-readable artifacts from the shared ADLC artifact repo, not chat memory.

Recommended inputs:

- Per-ticket `hitl.jsonl`.
- `goal.md`, `config.json`, and `status.md`.
- Eval JSON sidecars and final reports.
- Dependency maps and strategy notes.
- Artifact indices/rollups.

Monthly review should answer:

- Which failures were caused by ADLC skill behavior rather than ticket/product/platform issues?
- Which gates were skipped or over-triggered?
- Which docs caused confusion?
- Which eval/testability caveats repeated?
- Which Salesforce upstream changes or conflicts appeared?
- Which local overlay guidance needs to change?
- Which onboarding/install drift caused execution problems?

Output should be a proposed skill-improvement backlog, not automatic skill edits. Changes still need review, implementation, and regression.
