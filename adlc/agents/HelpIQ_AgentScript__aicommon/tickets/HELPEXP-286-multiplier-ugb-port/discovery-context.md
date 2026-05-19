# HELPEXP-286 — Discovery context

**Phase:** 3b complete (mental model + dependency map + testability).
**Built:** 2026-05-16, from Phase 3a SOQL + local `.agent` lines 261–313 (multiplier subagent block) + lines 366–425 (action definitions) + sibling-ticket prior HITL signals.

---

## Section 1 — Prompt Mental Model (instruction edit)

### Prompt purpose

Make `HelpIqAgentMultiplierSoftwareRequests` collect the three required slots (`applicationKey`, `accessTypeKey`, `reasonForAccess`) for a known catalog app and file a JSM ticket via the `flow://HelpIqAgentMultiplierSoftwareRequests` flow — while disambiguating qualifiers (e.g., Zoom vs Zoom Phone) and falling back to a knowledge-search escalation path for out-of-catalog asks.

### Structure (current legacy prompt — local file lines 267–301)

Four numbered top-level steps + three sub-steps under Step 2 + a Response Guidelines block. There is no `UNDERSTAND/GATHER/BUILD` decomposition, no Service Strategy taxonomy, and no explicit Confirm step.

```text
### 1. Validate the Application and Qualifier (MANDATORY FIRST STEP)
    ↳ if qualifier detected (Zoom Phone, etc.) → STOP, ask standard vs qualified
        ↳ qualified  → HelpIQ_QnA → Step 3
        ↳ standard   → Step 2

### 2. Fetch Application Access Details (Acknowledge and Pivot)
    PRIORITY: Always start with "I can definitely help you request access to [Application] right here!"
    ↳ Action: HelpIqAgentApplicationAccessDetails
       2A. user declines → HelpIQ_QnA + escalation check
       2B. multiple types → present + ask user to pick
       2C. unspecified/none/default → SILENCER RULE, call it "General"

### 3. Handle Knowledge Search & Escalation (Fallback Only)
    Action: HelpIQ_QnA + immediate escalation check

### 4. Create the Software Request
    Only after applicationKey + accessTypeKey + reasonForAccess obtained:
    Action: HelpIqAgentMultiplierSoftwareRequests

## Response Guidelines
    Acknowledgment Rule | No Internal Leaking | No Meta-Commentary
```

### Control flow

| Step | Decision point | Determines |
|---|---|---|
| 1 | Is there a qualifier (Phone/Cloud/Prod/etc.) in the utterance? | Branch to `qualified` (KB path + escalation) or `standard` (Step 2) |
| 2 | (none — mandatory action) | Always calls `HelpIqAgentApplicationAccessDetails`; the leading "PRIORITY" line emits the mandatory acknowledgement before the action |
| 2A | Did the user decline? | Branch to KB + escalation |
| 2B | Did `HelpIqAgentApplicationAccessDetails` return multiple access types? | Ask user to pick one |
| 2C | Is the returned access type "Unspecified/None/Default"? | Force value to "General"; check whether user provided a reason yet |
| 3 | (entry from Step 1 qualified, Step 2A decline, or implicit fallback) | Call `HelpIQ_QnA`, then offer escalation |
| 4 | Are all three slots filled? | Call `HelpIqAgentMultiplierSoftwareRequests` |

**No explicit Confirm step.** Step 4 fires the action as soon as the three slots are filled. The user is never shown a slot summary for go/no-go.

**No Answer concept.** Every catalog-app utterance flows toward Submit (Step 2 → Step 4) or escalation (Step 3). An informational utterance like "is Zoom Basic auto-provisioned?" either falls into Step 2 (mandatory acknowledgement → action call → response) or Step 3 (KB + escalation offer). There is no path that says "retrieval resolved your question, no action needed."

### Tool / action interaction

Three actions wired (local file lines 302–313, defined lines 319–425):

| Action | Target | Required inputs | Output | Description quirk |
|---|---|---|---|---|
| `HelpIQ_QnA` | `generatePromptResponse://HelpIQ_QnA` | `Input:Query`, `Input:RetrieverIdOrName`, `citationMode` | `promptResponse` (rich text) + `citations` | RAG via Glean retriever `ITKB_Confluence_Article_DMO_Retriever_…` |
| `HelpIqAgentApplicationAccessDetails` | `flow://HelpIqAgentGleanSearch` | `HelpIqGleanAgentId` (= `glean_agent_id` variable), `inputChatMessage` | `outputMessages` (list[object]) with elaborate ERROR_9999 + filter (`messageType=CONTENT`, `author=GLEAN_AI`) handling | Despite the name, this is a Glean-backed flow, not a separate Multiplier API |
| `HelpIqAgentMultiplierSoftwareRequests` | `flow://HelpIqAgentMultiplierSoftwareRequests` | `accessTypeKey`, `applicationKey`, `reasonForAccess` (all `is_required: True`) | `ticketURL` (rich text) with `<link \| Ticket>` format | **`require_user_confirmation: False`** — Salesforce's native confirmation flag is OFF. Submit fires as soon as the model decides to call. |

**`require_user_confirmation: False` is significant for Stage 0.** The platform's native "confirm before action" UI is not in use. AC #2 (Confirm-before-Submit) must be enforced by either:

- **Option A.** Flip `require_user_confirmation: True` on the action → Salesforce shows native confirm UI for every Submit. Simple but changes UX in a Salesforce-defined way (the native confirm prompt may not present the slot summary the way we want).
- **Option B.** Prompt-only Confirm step in the new `reasoning.instructions` → model must comply on every turn. HELPEXP-274 prior HITL (slot-template-beats-countable-rule, 2026-05-09) says structural/slot prompts beat countable rules; a structured Confirm template can work but model compliance is non-zero risk.
- **Option C.** Agent Script variable + conditional guard. Add a `mutable bool confirmation_accepted` variable; set it true in a Confirm turn; gate `HelpIqAgentMultiplierSoftwareRequests` invocation behind `if @variables.confirmation_accepted`. Highest determinism.

This is the canonical Stage 0 design decision. The ticket's Requirement #7 explicitly invites this trade-off ("use Agent Script structural mechanisms where they meaningfully improve reliability over prompt-only narrative").

### Variables in scope

| Variable | Type | Default | Used by |
|---|---|---|---|
| `glean_agent_id` | `mutable string` | `"3e15d8c322254dc693849db144d67941"` | `HelpIqAgentApplicationAccessDetails.HelpIqGleanAgentId` |
| `prompt_template_retriever_id` | `mutable string` | `"ITKB_Confluence_Article_DMO_Retriever_1Cx_FJRa7b15a1a"` | `HelpIQ_QnA.Input:RetrieverIdOrName` |

No slot-tracking variables today. Stage 0 will likely add at least one (Option C above) and may add more depending on the design (e.g., `app_identity_resolved`, `beneficiary_resolved` if disambiguation is structural).

### Load-bearing scaffolding (do not remove without explicit replacement)

- **Catalog block in `description:`** (local file lines 263–265) — feeds the router's classifier; removing or trimming it changes what utterances route to multiplier vs GeneralQnA. **Preserve verbatim** per ticket requirement #8.
- **`HelpIqAgentApplicationAccessDetails.inputChatMessage` description** — "Find application name from the conversation and send only application or software name." This shapes how the model constructs the tool input. Preserve.
- **`HelpIqAgentApplicationAccessDetails.outputMessages` description** — the ERROR_9999 handling and Glean filter logic. The model's BUILD turn reads `messageType=CONTENT` + `author=GLEAN_AI` fragments from this. Preserve as-is or transplant unchanged.
- **`HelpIqAgentMultiplierSoftwareRequests.ticketURL` description** — the `<link \| Ticket>` format. Submit completion message reads this. Preserve.
- **Global system instruction** (file lines 14–37) — "Never answer a question without first using a knowledge search action" + tone + Slack-formatting rules. The multiplier topic inherits all of these. Some are in tension with the planned UGB structure (e.g., the global "Never answer without KB search" technically conflicts with the new Answer path when retrieval already happened — though the playbook's intent for global is preserved).

### Existing coverage (where current prompt already partially addresses ticket goals)

| AC | Current prompt coverage |
|---|---|
| AC #2 Confirm-before-Submit | **None.** Step 4 fires Submit as soon as slots fill. |
| AC #3 Answer-vs-Submit | **None.** No Answer concept. |
| AC #4 5-bucket coverage | **Partial.** Step 1 qualifier branch ≈ Clarify; Step 2A decline ≈ Escalate offer; Step 4 ≈ Submit. No Answer; no explicit Confirm. |
| AC #5 GATHER correctness + no internal leaks | **Partial.** "No Internal Leaking" rule under Response Guidelines exists. `accessTypeKey`/`applicationKey` slot collection is named in Step 4 prerequisites. |
| AC #6 GATHER-informed Clarify | **Partial.** Step 2B says "present the options clearly and ask the user to select one" but no slot template, no escape hatch, no Acknowledgment-Question-Options structure. |

### Conflicts and contradictions (vs ticket requirements)

| Conflict | Where in current prompt | What ticket requires | Severity |
|---|---|---|---|
| No Confirm step → Submit fires immediately on slot completion | Step 4 ("Only after `applicationKey + accessTypeKey + reasonForAccess` obtained: invoke the action") | AC #2 — every Submit preceded by accepted Confirm (100%) | **Blocking** |
| No Answer path → all catalog-app asks queue Submit or escalate | Step 2 mandatory acknowledgement ("I can definitely help you request access to [Application] right here!") commits to action framing regardless of intent | AC #3 — informational utterances reach Answer ≥80% | **Blocking** |
| Step 2 PRIORITY mandatory script verbatim ("I can definitely help…") fires on every multiplier-routed utterance | Lines 277–278 | Conflicts with Answer turn (would prepend an action offer to what should be an informational reply) and with Clarify turn (would prepend an action offer before disambiguating); also documented as a quality issue in `multiplier-current-state.md` §2.3 ("stilted prose" / "bolted on regardless of whether it makes sense") | **Blocking** (must be removed or scoped to Submit path) |
| All-caps emphasis ("MANDATORY", "PRIORITY", "FORBIDDEN", "SILENCER RULE") | Throughout Steps 1, 2, 2C | Prompt-engineering playbook warns against "louder text" and recommends slot templates instead | **Strong** (style + reliability) |
| 4 sequential branchy steps without top-level Service Strategy classification | Whole prompt | Prompt-engineering playbook Service Strategy decomposition + 5-bucket BUILD discipline | **Blocking** (structural) |
| `require_user_confirmation: False` on the Submit action | Local file line 396 | AC #2 needs SOME confirmation mechanism (prompt slot, native UI, or variable guard) | **Strong** — Stage 0 design decision |
| No app-qualifier disambiguation for cases beyond a literal substring (Tableau Creator vs Viewer, Claude Desktop vs Claude Code, Salesforce orgs) | Step 1 only triggers on substring qualifiers like "Phone"/"Cloud"/"Prod"/"Sandbox" | AC #4 — must cover qualifier-disambiguation behavioral category for ≥1 scenario | **Medium** (extend Step 1 logic or replace with UGB UNDERSTAND classification) |
| "General" silencer rule is conflated with Submit-trigger (Step 2C jumps to Step 4) | Lines 286–289 | Preserve "General" silencer rule per ticket requirement #8, BUT the Submit jump must be gated by Confirm | **Medium** — preserve the rule, change the surrounding flow |
| Global system "Never answer a question without first using a knowledge search action" | File line 15 | Answer turn (AC #3) may answer from retrieval, but a generic catalog-knowledge response (e.g., "Zoom Basic is auto-provisioned") would still need GATHER to fire — needs to be threaded carefully | **Low** if GATHER always fires before Answer; **Medium** if not |

### Candidate insertion points (if we were going targeted-edit)

We are not going targeted-edit (see structure assessment below). For the record, if we were:
- Replacing Step 4 with a Confirm gate before invocation would be the narrowest viable edit, but it doesn't add the Answer path and doesn't fix the misclassification of every utterance as action-bound.
- Adding a pre-Step-1 classification ("first decide if this is informational vs action") would attempt the Answer/Submit split but layered on the legacy 4-step prose — likely produces confusing instruction soup.

### Structure assessment: `restructure-recommended`

Per `adlc/playbooks/prompt-engineering-playbook.md` §5 (`Targeted Edit Vs Restructure Gate`), restructure is recommended when **any** of these hold:

> - Current instructions directly contradict each other in a way that blocks the goal.
> - The prompt lacks a reliable control flow for understanding, gathering, and building responses.
> - The targeted edit would require scattered overrides in multiple sections.

All three hold here:

1. **Direct contradiction:** Step 2's PRIORITY mandatory action-framing line conflicts with the planned Answer path (which is informational, no action queued). You cannot keep both.
2. **No reliable UGB control flow:** The current prompt has no UNDERSTAND classification step; it dispatches on substring qualifier detection then immediately commits to action framing. There's no place to insert "is this informational vs action?" without rebuilding the spine.
3. **Scattered overrides:** Adding Confirm-before-Submit + Answer path + 5-bucket Service Strategy as additive edits would require touching Steps 1, 2, 2A, 2B, 2C, 3, and 4 simultaneously — i.e., it's already a restructure even if labeled "targeted."

**HITL satisfaction:** The playbook requires HITL before restructure implementation. The ticket's own Stage 0 HITL gate (structural design review before any prompt text is drafted) satisfies this requirement.

---

## Section 2 — Dependency Map

### Agent / org / topic

| Field | Value |
|---|---|
| Agent | `HelpIQ_AgentScript` (label `HelpIQ-AgentScript`) on `aicommon` (`indeedinc--aicommon.sandbox.my.salesforce.com`, orgId `00DEm00000IA4w4MAD`) |
| Bot Definition Id | `0XxEm0000006ufRKAQ` (Type `InternalCopilot`) |
| Active version | v7 (BotVersion Id `0X9Em0000003HltKAE`, model `model://sfdc_ai__DefaultGPT52`) |
| Affected topic | `HelpIqAgentMultiplierSoftwareRequests` (v7 GenAiPluginDefinition `179Em000000DqC9IAK`) |
| Adjacent topics (not modified) | `GeneralQnA_HelpIQ`, `Off_Topic`, `Ambiguous_Question`, `Escalation` |

### Routing / classification surfaces

- **`agent_router` reasoning instructions** (local file lines 65–67): `"If intent is software access/licensing, use go_to_HelpIqAgentMultiplierSoftwareRequests; otherwise use go_to_GeneralQnA_HelpIQ."`
- **Multiplier topic `description:`** (lines 263–265): the ~33-app catalog list. The router's classifier reads topic descriptions to decide routing — modifying the description will likely shift routing.
- **Adjacent topic routing risk:** Out-of-scope for this ticket. The 2026-05-13 deferral confirms: "Router routes bare app names to software-access. Bare `slack` (or any catalog app name with no other context) is classified as a software-access request by agent_router."

### Global instructions

`system.instructions` (lines 14–37) sets the IT-assistant persona, the FORMATTING/SECURITY/HANDLING rules, and the "Never answer a question without first using a knowledge search action" line that interacts with the new Answer path. Out of scope for editing; in scope for awareness.

### Actions, backing targets, input/output fields

Covered in Section 1 (Tool / action interaction). Summary:

- `HelpIQ_QnA` → `generatePromptResponse://HelpIQ_QnA` (RAG; uses Glean retriever `ITKB_Confluence_Article_DMO_Retriever_1Cx_FJRa7b15a1a`)
- `HelpIqAgentApplicationAccessDetails` → `flow://HelpIqAgentGleanSearch` (Glean lookup by app name; returns access types/keys)
- `HelpIqAgentMultiplierSoftwareRequests` → `flow://HelpIqAgentMultiplierSoftwareRequests` (creates the JSM ticket — real side effect)

### Variables / context / permissions

| Surface | Detail |
|---|---|
| Linked variables | None at the topic level today; Stage 0 may introduce `confirmation_accepted` or similar slot variables |
| Mutable variables | `glean_agent_id`, `prompt_template_retriever_id` (both string, defined at agent level) |
| Session / user / account context | Topic is an Employee Agent (`AgentforceEmployeeAgent`) — no MessagingSession / RoutableId / Account binding. Identity comes from the authenticated Slack/internal session. |
| Routable ID needed for testing? | **No.** Knowledge-only + retriever + action call. No account-specific data. |
| Permissions / tokens | Glean lookup requires the Einstein Agent User to have flow execution permissions for `HelpIqAgentGleanSearch` and `HelpIqAgentMultiplierSoftwareRequests`. Verified implicitly by HELPEXP-274 successful runs in this org. |
| External systems | Glean (read), JSM (write — the Submit action). |
| Retriever / RAG | Glean retriever `ITKB_Confluence_Article_DMO_Retriever_1Cx_FJRa7b15a1a`. Subject to KB ingestion lag (~1 week sync per discovery transcript) — relevant for new-article scenarios but out of scope. |

### Lower-env vs production gaps

| Capability | Lower env (aicommon sandbox) | Production |
|---|---|---|
| Topic routing | Same router prompt, same model | Same |
| `HelpIQ_QnA` RAG | Live Glean retriever (read-only) | Live Glean retriever |
| `HelpIqAgentApplicationAccessDetails` Glean lookup | Live Glean (read-only) | Live Glean |
| `HelpIqAgentMultiplierSoftwareRequests` Submit | **Live JSM ticket creation** — pollutes the queue if not mocked | Live JSM |
| Model | `sfdc_ai__DefaultGPT52` | Same |
| KB content | Identical (Glean is org-wide) | Same |

**Material gap:** Submit creates a real JSM ticket. Mitigation locked in Phase 2: `sf agent preview --simulate-actions` default; HITL gate after first sandbox run to confirm/adjust.

### Per-requirement testability classification

| AC | Classification | Why | What's needed to test |
|---|---|---|---|
| AC #1 — Regression floor (5pp band) | `fully-testable-lower-env` | Existing 999-case Test Center suite runs against any deployed BotVersion in `aicommon` | Confirmed test definition name (registry: `HelpIQ_GPT52_v7_baseline_5_14_1`); deploy new BotVersion bound to the suite via `subjectVersion` |
| AC #2 — Confirm-before-Submit (100%) | `partially-testable-lower-env` | Tool call sequencing is fully observable via session traces (`.sfdx/agents/.../traces/`); requires multi-turn fixtures with explicit accept/reject responses | 10–15 multi-turn YAMLs with scripted "yes" and "no" replies at Confirm; trace inspection of `HelpIqAgentMultiplierSoftwareRequests` invocations |
| AC #3 — Answer-vs-Submit (≥80%) | `partially-testable-lower-env` | Same trace-inspection capability; needs scenarios that split on intent (informational vs action) | Hand-authored scenarios with paired Answer-intent and Submit-intent variants; rubric grading from trace output (not user-facing message — HELPEXP-274 noted planner-level markdown stripping) |
| AC #4 — Behavioral & catalog coverage (5 buckets + 5 categories + ≥8 apps) | `fully-testable-lower-env` | Scenario design, not runtime behavior | Authored scenarios meeting coverage table |
| AC #5 — GATHER tool-call correctness (≥90%) | `partially-testable-lower-env` | `simulate-actions` returns canned data, so the `applicationKey` arg shape is observable but Glean's *real* return shape is not. Live Glean (read-only) is preferred for this AC. | Either: (a) live Glean calls during this AC's evaluation (safe — read-only), or (b) realistic mocks per app. **Recommend (a) for this AC.** |
| AC #6 — GATHER-informed Clarify (≥70%) | `partially-testable-lower-env` | Requires retrieval to return *multi-option* results, which depends on real Glean data for the specific apps tested | Same as AC #5 — live Glean for this AC; pick apps known to return multiple access types (Tableau, Salesforce, Adobe, Figma per discovery transcript) |
| AC #7 — Determinism (N=3, ≥90% class + ≥85% slot) | `fully-testable-lower-env` | Just repeat-runs of the same fixtures | Subset of 5–7 scenarios + `--simulate-actions` to remove Glean variance from the determinism signal |

**Critical scenarios that are NOT testable in lower env:** None. All ACs are at least partially testable. No `not-lower-env-testable` classifications.

**Note on rubric grading:** Per HELPEXP-274 prior HITL (2026-05-09T20:10Z), Salesforce's planner step normalizes user-facing output (strips bold + number prefixes). For AC #2 / AC #3 / AC #7 rubric grading, **inspect trace LLM step raw output** at `.sfdx/agents/<agent>/sessions/<sid>/traces/<traceId>.json`, NOT the rendered user-facing message. This is a methodology requirement, not a testability blocker.

**Note on tool mocking vs live calls:**
- AC #1 (regression floor) — Test Center suite uses whatever the suite is configured with (likely live actions; we don't change that)
- AC #2 / AC #3 / AC #4 / AC #7 — `simulate-actions` is sufficient (we care about model decisions, not tool returns)
- AC #5 / AC #6 — live Glean recommended (read-only, safe)

For Submit specifically, simulate-actions everywhere — we never want a real JSM ticket from a rubric run.

### Adjacent-topic regression

Out of scope for this ticket per Phase 2 scope decision. The 999-case Test Center suite covers adjacent topics implicitly and AC #1's regression floor is the safeguard. If multiplier prompt edits cause router-classifier drift (unlikely, since we're not changing the topic `description:`), AC #1 will catch it.

---

## Open methodology questions for Phase 3c

1. **Test definition name for AC #1.** Registry says `HelpIQ_GPT52_v7_baseline_5_14_1`. Need to confirm presence in org via `sf data query` on `AiEvaluationDefinition` before Phase 5 runs.
2. **Live Glean vs simulate-actions for AC #5/#6.** Phase 3c will document the mixed strategy in the test plan.
3. **Multi-turn runner.** `sf agent preview send` with static `conversationHistory` YAML is the deterministic path. Scripted-variation YAMLs (per the 2026-05-13 draft's idea) are NOT needed for today's leaner draft — we use deterministic conversation histories per scenario.
4. **Trace export.** For rubric grading we need trace JSON. The path `.sfdx/agents/<agent>/sessions/<sid>/traces/<traceId>.json` is established from HELPEXP-274. Need to script a small extractor that pulls the LLM step raw output per turn — Phase 5 concern but mention in Phase 3 plan.

---

## What 3b did NOT do

- **Did not draft replacement prompt text.** That's Stage 1 in Phase 5, after Stage 0 structural design HITL approval.
- **Did not commit to Option A/B/C for Confirm enforcement.** That's the Stage 0 deliverable.
- **Did not audit `GeneralQnA_HelpIQ` for spillover risk.** Out of scope per Phase 2.
