# Multiplier Software Requests — Ticket Draft

**Status:** Draft (pre-JIRA). Move into `adlc/agents/HelpIQ_AgentScript__aicommon/tickets/{KEY}-{short-description}/` once a JIRA key is assigned.
**Owner:** Oliver Guzman
**Drafted:** 2026-05-13. Revised 2026-05-16.

---

## Context

The `HelpIqAgentMultiplierSoftwareRequests` sub-agent currently routes most software-access requests directly into ticket creation with minimal upstream discovery. Per the 2026-05-13 discovery transcript with Anthony, HelpIQ should mirror the JSM portal's pre-submission slot-filling behavior: identify the app, confirm what kind of access, and only then file. Today most of that happens (or fails to happen) inside the ticket comment thread, after the user has already disengaged.

In Test Center bulk runs (HELPEXP-274 baseline, 999 utterances), `MultiplierSoftwareRequests` is the highest-performing topic on coherence (99%) and action_completion completeness (95%). Conciseness sits at 82%, completeness on multiplier rows at 85%. The structural port must not regress those numbers.

Discovery (`adlc/agents/HelpIQ_AgentScript__aicommon/multiplier-current-state.md` and `multiplier-discovery-transcript.md`) surfaced five contradictions in the current multiplier prompt that targeted edits cannot resolve structurally — Step 1 vs Step 2 race, PRIORITY language vs Confirm gate, implicit Step 4 prerequisites, escalate-without-execute, output guideline ambiguity. A unified UGB (UNDERSTAND → GATHER → BUILD) restructure with 5-bucket Service Strategy (`Clarify / Answer / Confirm / Submit / Escalate`) is the proposed shape, ported from the HELPEXP-274 General QnA pattern.

---

## Requirements

1. **Restructure `reasoning.instructions` into UGB phases** (UNDERSTAND → GATHER → BUILD) for the multiplier sub-agent only. No other sub-agent is in scope.
2. **Apply the 5-bucket Service Strategy** in BUILD: `Clarify / Answer / Confirm / Submit / Escalate`. Reference: `adlc/playbooks/prompt-engineering-playbook.md` lines 414-431. Multiplier is the canonical action-with-info-layer example — it has both an info layer (`HelpIqAgentApplicationAccessDetails` retrieval can resolve questions without action) and an action layer (`HelpIqAgentMultiplierSoftwareRequests` requires Confirm before Submit).
3. **Confirm-before-Submit gate.** Submit (the action call) cannot fire without a prior turn in the same conversation where the agent presented a slot summary and the user explicitly accepted (yes / equivalent).
4. **Answer path is distinct from Submit.** Informational utterances (e.g., "is Zoom auto-provisioned?") are answered from retrieval, no action queued. Optional follow-on offer ("want me to file a ticket?") is allowed but not required.
5. **App and qualifier disambiguation.** Cases like "Zoom" vs "Zoom Phone", "Claude Desktop" vs "Claude Code", "Tableau Creator" vs "Tableau Viewer" trigger a Clarify before any retrieval or Submit.
6. **GATHER-informed Clarify.** When access-details retrieval returns multi-option results (license tiers, multiple access types), the next Clarify uses those returned options rather than defaulting to "General" and skipping the slot.
7. **Use Agent Script structural mechanisms where they meaningfully improve reliability over prompt-only narrative.** This is the part the prompt language alone can't enforce — slot tracking across turns, gating an action behind a confirmed flag, deterministic routing on a condition. The coding agent picks the right primitives from the references in §Examples (variables, lifecycle hooks, conditional expressions, action chaining) and justifies the choice in the Stage 0 deliverable. If prompt-only is the right answer for a given concern, that's also a valid choice — say so and why.
8. **Preserve verbatim:** the catalog `description` block (~33 apps), all action contracts and slot names (`accessTypeKey`, `applicationKey`, `reasonForAccess`), the "General" silencer rule for unspecified/none/default access types, and the no-internal-leaking rule (tool names, internal keys, document names).

### Out of scope

The following were surfaced during discovery and are **not** in this ticket. Each must be documented in `multiplier-out-of-scope.md` at closeout with a one-paragraph problem statement and recommended owner.

- On-behalf-of / beneficiary handling
- License-type matrix expansion (Salesforce, Tableau tiers, etc.)
- Bulk requests, catalog-miss "Other" path, geo / role pre-screen
- Reasoning-trajectory rubric and LLM-as-judge build (better as a cross-sub-agent ticket)
- Router miss / welcome-message fallback (cross-cutting platform issue)
- KB ingestion lag, catalog source-of-truth drift (operational)

---

## Execution / Staging

**Version strategy.** Clone the current Active BotVersion into a **new** BotVersion. All changes target the new version. Do not edit the current Active version in place — it stays untouched as the regression baseline.

**Stage 0 — Agent Script structural design.** Before any `reasoning.instructions` text is drafted, produce `eval/agent-script-design.md` covering:

1. **Slot inventory.** Each piece of state the multiplier needs to track across turns (app identity, qualifier resolution, access type, reason for access, confirmation acceptance, etc.). For each slot: where it gets set, where it gets read, where it gets passed to the action.
2. **Mechanism choice per slot.** Variable vs prompt-only vs action input parameter. Each justified against reliability requirements. Validate syntax against the references in §Examples before committing.
3. **Lifecycle hook usage.** Whether `before_reasoning` or `after_reasoning` hooks are needed and what they enforce. Tie each hook to an acceptance criterion it makes pass — if a hook can't be tied to a criterion, it shouldn't be in the design.
4. **Confirm gate enforcement.** How "Submit cannot fire without an accepted Confirm" is enforced — structural (a variable or conditional guarding the action invocation) vs prompt-only. If prompt-only, justify why.

**HITL gate:** user reviews and approves the structural decisions before prompt text is drafted.

**Stage 1 — Prompt edit.** Single combined rewrite of `reasoning.instructions` into UGB phases with 5-bucket Service Strategy, integrating the structural mechanisms approved in Stage 0.

---

## Acceptance Criteria

| # | Criterion | Threshold | Blocking |
|---|---|---|---|
| 1 | **Regression floor** — no multiplier-correctly-routed metric (coherence, completeness, conciseness, output_validation, action_completion completeness) drops more than 5pp vs the current Active version baseline on the existing 999-case Test Center suite | ±2pp counts as flat | Yes |
| 2 | **Confirm-before-Submit** — every Submit action invocation in multi-turn test scenarios is preceded by an accepted Confirm in a prior turn of the same conversation | 100% on multi-turn scenarios | Yes |
| 3 | **Answer-vs-Submit classification** — informational utterances reach Answer (not Submit); action-typed utterances reach Confirm-then-Submit | ≥80% on hand-authored multi-turn scenarios | Yes |
| 4 | **Behavioral and catalog coverage** — multi-turn set covers (a) all five Service Strategy buckets and (b) at least one example per behavioral category: multi-license/tier, qualifier-disambiguation, multi-option retrieval, auto-provisioned (Answer path), straightforward action (Confirm + Submit). At least 8 distinct catalog apps overall. | All 5 buckets + all 5 categories + ≥8 apps | Yes |
| 5 | **GATHER tool-call correctness** — when GATHER fires for a catalog app, the agent calls `HelpIqAgentApplicationAccessDetails` with an `applicationKey` matching the user's intended app. No internal keys leaked in user-facing output. | ≥90% on multi-turn scenarios that reach GATHER | Yes |
| 6 | **GATHER-informed Clarify** — when retrieval returns multi-option results, the next Clarify uses those options rather than defaulting | ≥70% on hand-authored multi-option scenarios | No (flag failures, don't gate close) |
| 7 | **Determinism / repeatability** — a representative subset of multi-turn scenarios (5-7) is run N=3 times; same Service Strategy classification + same slot summary on the Confirm turn across runs. This is the test of whether structural primitives are doing their job vs prompt-only narrative. | ≥90% same-classification + ≥85% same-slot-summary across runs | Yes |

Coding agent has discretion on specific test utterances. Recommended: 10-15 multi-turn scenarios total. Single-turn coverage of all ~33 catalog apps comes from the existing 999-case regression suite — no need to re-author single-turn cases.

---

## Agent & Topic

- **Org:** `aicommon` (sandbox)
- **Agent:** `HelpIQ-AgentScript` (API name: `HelpIQ_AgentScript`)
- **Sub-agent under modification:** `HelpIqAgentMultiplierSoftwareRequests` (only — no edits to other sub-agents)
- **Active version:** discover at session start (`AGENT_VERSION_REGISTRY.md` + verify against the org)
- **Authoring bundle source:** `force-app/main/default/aiAuthoringBundles/HelpIQ_AgentScript/HelpIQ_AgentScript.agent`
- **Action / retrieval definitions:** `force-app/main/default/genAiFunctions/HelpIqAgentApplicationAccessDetails/`, `force-app/main/default/genAiFunctions/HelpIqAgentMultiplierSoftwareRequests/`
- **Version registry:** `adlc/agents/HelpIQ_AgentScript__aicommon/AGENT_VERSION_REGISTRY.md` — append a row at version transition.

---

## Baseline

- **Regression suite:** existing 999-case Test Center suite from HELPEXP-274 (API name confirmed at session start; current known: `HelpIQ_GPT52_v7_baseline_5_14_1`).
- **Multiplier baseline reference:** current Active BotVersion. HELPEXP-274 modified the General QnA sub-agent only — multiplier prompt content is unchanged across recent published versions, so the baseline is the same regardless of which version is currently Active.
- **Pre-ticket evidence brief:** `adlc/agents/HelpIQ_AgentScript__aicommon/multiplier-current-state.md` (per-version pass rates, action sequence distribution, concrete failure samples).

---

## Examples

**Discovery and prior work:**
- Discovery transcript: `adlc/agents/HelpIQ_AgentScript__aicommon/multiplier-discovery-transcript.md` (2026-05-13). Source of the JSM portal mirroring requirement.
- Existing multi-turn fixtures: `~/HelpIQ-Evaluation/evals/scenarios/SW-ACCESS-*.yaml` (4 scenarios; reusable starting point).
- UGB pattern precedent: `adlc/agents/HelpIQ_AgentScript__aicommon/tickets/HELPEXP-274-generalqna-phased-prompt/GENERALQNA_REASONING.md`.
- Service Strategy 5-bucket reference: `adlc/playbooks/prompt-engineering-playbook.md` lines 414-431.

**Agent Script references** (for Requirement #7 and Stage 0 design):
- Salesforce official: <https://developer.salesforce.com/docs/ai/agentforce/guide/agent-script.html> — variables, conditional expressions, transitions, tools.
- `developing-agentforce` skill (autoloads when editing `.agent` files): `~/.cursor/skills/developing-agentforce/`.
  - `references/agent-script-core-language.md` — syntax reference.
  - `assets/patterns/lifecycle-events.agent` — concrete `before_reasoning` / `after_reasoning` example with variables and conditional routing.
  - `assets/patterns/critical-input-collection.agent`, `assets/patterns/multi-step-workflow.agent` — patterns directly relevant to slot-filling and Confirm-before-Submit.
- In-codebase example: the existing `force-app/main/default/aiAuthoringBundles/HelpIQ_AgentScript/HelpIQ_AgentScript.agent` already uses Agent Script primitives — read it for project-conventional syntax before introducing anything new.
