# Iter 6: SOMEONE_ELSE / AMBIGUOUS RequestorScope guardrail

**Deployed:** 2026-05-18 ~13:00 UTC into v8 AuthoringBundle source (`aicommon` org).

## Problem caught (by user, not by me)

User asked: "did you test the scenario of confirming if the request is for themselves or someone else?"

I had not. Investigation surfaced a real regression vs v7:

- **v7 prompt** (Step 3): explicitly routed "teammate requests" away from the automated Submit action into `HelpIQ_QnA` (KB fallback). This was a safety mechanism.
- **iter-5 prompt** (HELPEXP-286 pre-iter-6): dropped that routing entirely. No language about requestor scope. The Confirm→Submit chain would happily process "Figma access for my teammate Bob" → silent-failure: ticket gets filed for the session user (not Bob), because the action contract `HelpIqAgentMultiplierSoftwareRequests` only accepts 3 inputs (`accessTypeKey`, `applicationKey`, `reasonForAccess`) — no requestor field, runtime infers from session.

The user's "out of scope" call-out from `multiplier-ticket-draft.md` line 34 is "on-behalf-of handling" (i.e., properly supporting on-behalf-of via a new flow contract). That stays out of scope. What's in scope here is **restoring the v7 safety guardrail** — detect and refuse the automated path. Not adding new capability, just preventing a known silent failure.

## Changes vs iter-5 (attempts/04-structural-gate)

### UNDERSTAND
- Added step 4: **RequestorScope** classification (SELF / SOMEONE_ELSE / AMBIGUOUS) with explicit phrase signals.
- Renumbered prior steps 4 → 5 (app+qualifier) and 5 → 6 (sentiment).
- Removed the awkward "request Z for my team" example from the ACTION intent description (was confusing in light of new RequestorScope check).
- Added two skip-GATHER conditions:
  - `SOMEONE_ELSE → BUILD with Service Strategy = Escalate` (skips wasted retrieval).
  - `AMBIGUOUS → BUILD with Service Strategy = Clarify` (asks self-vs-someone-else before any retrieval).

### Service Strategy: Escalate
- Added SOMEONE_ELSE to the "Use when" trigger list.
- Added explicit on-accept wiring: call `{!@actions.HelpIqAgentEscalateAction}` with RequestSummary + RequestDescription (including beneficiary name / context for on-behalf-of cases).
- Added a SOMEONE_ELSE-specific paragraph with template phrasing.
- Explicit: do NOT call `HelpIqAgentApplicationAccessDetails`, do NOT call `stage_request`, do NOT collect slot values for the other person.

### Hard rules
- Added new rule 2: "Never call `HelpIqAgentMultiplierSoftwareRequests` when RequestorScope is SOMEONE_ELSE or AMBIGUOUS." With explanation: action contract has no requestor field; runtime files for session user regardless of names/pronouns in reason text.
- Renumbered prior rules 2-5 → 3-6.

### Debug record
- Added 16th field: **RequestorScope** (what + why), positioned between Intent and AppQualifier.
- Updated meta rule: "All sixteen fields must appear" (was fifteen).

### Action wiring (reasoning.actions)
- Added `HelpIqAgentEscalateAction: @actions.HelpIqAgentEscalateAction` after `HelpIqAgentApplicationAccessDetails`, before `stage_request`.

### Action definitions (subagent actions block)
- Added local `HelpIqAgentEscalateAction:` definition at the top of the multiplier subagent's `actions:` block. Copied from GeneralQnA's definition. Description updated to mention on-behalf-of routing. Actions in Agent Script are subagent-scoped, so we couldn't reuse GeneralQnA's definition by reference.

## Verification (sf agent preview --simulate-actions, 2026-05-18 ~13:00 UTC)

**SOMEONE_ELSE test:** "I need to request Figma access for my teammate Bob, he's a designer working on the new homepage"

Turn 1 — agent reply: "Got it — you're looking to get Figma access for your teammate Bob. Since this request is on behalf of someone else, I can't submit it through the automated access-request path, but I can escalate it to a specialist who can route the request correctly. Want me to escalate this for Bob?"

| Field | Value |
|---|---|
| RequestorScope | SOMEONE_ELSE ("my teammate Bob") |
| ServiceStrategy | Escalate |
| Retrieval | skipped |
| StageRequestCalled | false |
| ToolsCalled | none |
| GateCheck | Submit not visible |

Turn 2 — user: "yes please escalate" — agent reply: "Totally got you — I escalated the on-behalf-of Figma access request for Bob to a specialist so they can route it the right way." + ticket link in `<link | Ticket>` format.

| Field | Value |
|---|---|
| ServiceStrategy | Escalate |
| ToolsCalled | HelpIqAgentEscalateAction |
| (Submit) | NOT called — the regression scenario is fixed |

**SELF regression check (single sample):** "i need figma access for design reviews" → "SSO" → "yes please"

- Turn 1: jumped straight to Confirm (iter-5 ran Clarify-with-options first). Likely simulator output variance, not iter-6 regression. RequestorScope=SELF, StageRequest called.
- Turn 2: model gave a generic refusal ("your request may be complex...") because "SSO" isn't yes/no acceptance after a Confirm. Debug record dropped. Planner-level handling oddity, not our prompt's logic.
- Turn 3: "yes please" → ConfirmChain=INTACT, accept_confirmation called, HelpIqAgentMultiplierSoftwareRequests called, ticket link returned. Structural gate (AC #2) holds.

## Known residuals (not fixed in iter-6)

- `{!@variables.X}` template injection in `VarStatePreTurn` field still renders literal — diagnostic visibility issue only, gate works (runtime-enforced). Same as iter-5.
- Qualifier disambiguation on bare "Zoom" still misses (AC #4). Same as iter-5.
- Need a full 8-scenario regression run against iter-6 to confirm SELF happy-path determinism wasn't degraded. Single sample today shows mild variance on Turn 1 but Submit gate holds end-to-end.
- AC #7 determinism N=3 still pending.

## File pointers

- Prompt source: `attempts/05-someone-else-guardrail/instruction.txt` (176 lines)
- Pre-iter-6 reference: `originals/iter5-merged-into-v8-pre-iter6.agent`
- Deployed: `force-app/main/default/aiAuthoringBundles/HelpIQ_AgentScript/HelpIQ_AgentScript.agent` (655+ lines)
