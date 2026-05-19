# HELPEXP-286 — Multiplier UGB port (Confirm-before-Submit + Answer-vs-Submit)

**Status:** Phase 3a discovery — canonical folder created.
**Owner:** Oliver Guzman (`obguzman`).
**Drive session opened:** 2026-05-16.
**Canonical ticket source:** Local file `adlc/agents/HelpIQ_AgentScript__aicommon/multiplier-ticket-draft.md` (revised 2026-05-16), confirmed by user as the text they pasted into JIRA HELPEXP-286.
**JIRA pull status:** Not verified independently — `user-atlassian` OAuth was skipped; `user-jira` MCP account has zero project visibility. Local draft treated as authoritative per user approval.

---

## Summary

Restructure `HelpIqAgentMultiplierSoftwareRequests` `reasoning.instructions` from the legacy "MANDATORY FIRST STEP / PRIORITY / SILENCER" prose into the same **UNDERSTAND → GATHER → BUILD (UGB)** shape that HELPEXP-274 established for `GeneralQnA_HelpIQ`, but adapted for an *action-with-info-layer* sub-agent — **5-bucket Service Strategy** (`Clarify / Answer / Confirm / Submit / Escalate`) instead of GeneralQnA's 3-bucket.

The load-bearing structural changes are:

- **Confirm-before-Submit gate.** No `HelpIqAgentMultiplierSoftwareRequests` (ticket-creation) action call without an explicit user "yes" on a prior-turn slot summary. Zero-Confirm Submits are a blocking failure per prompt-engineering playbook.
- **Answer-vs-Submit split.** Informational utterances ("is Zoom Basic auto-provisioned?") get an Answer turn from retrieval; only action utterances queue Confirm + Submit. Misdirection either way is a production failure (annoyed users from unnecessary tickets; missed access from incorrect Answer).
- **App / qualifier disambiguation** as a Clarify before retrieval (Zoom vs Zoom Phone, Claude Desktop vs Claude Code, Tableau Creator vs Viewer).
- **GATHER-informed Clarify.** When `HelpIqAgentApplicationAccessDetails` returns multi-option results, the *next* Clarify uses those options rather than defaulting to "General".
- **Preserve verbatim:** the ~33-app catalog block, action contracts (`accessTypeKey`, `applicationKey`, `reasonForAccess`), the "General" silencer rule for unspecified access types, and the no-internal-leaking rule.

And — newly framed in this ticket — a **Stage 0 Agent Script structural design deliverable** (`eval/agent-script-design.md`) that decides per-slot which behaviors to enforce with Agent Script primitives (variables, lifecycle hooks, conditional expressions, action chaining) versus prompt-only narrative, gated by a HITL review before any prompt text is drafted.

## Scope

**In scope.** `HelpIqAgentMultiplierSoftwareRequests` `reasoning.instructions` rewrite; Stage 0 Agent Script structural design; multi-turn scenario suite (10–15 scenarios spanning ≥8 distinct catalog apps with a mix of license-required / auto-provisioned / qualifier-bearing / catalog-miss); new BotVersion cloned from v7 Active; preserve verbatim the ~33-app catalog block, action contracts, "General" silencer rule, and no-internal-leaking rule.

**Adjacent — NOT touching this iteration.** Other sub-agents (`GeneralQnA_HelpIQ`, `Off_Topic`, `Ambiguous_Question`, `Escalation`); `agent_router.reasoning.instructions` (changes there could re-route utterances away from multiplier and are excluded for scope safety); global `system.instructions`; the three backing flows / Apex / prompt templates (`flow://HelpIqAgentGleanSearch`, `flow://HelpIqAgentMultiplierSoftwareRequests`, `generatePromptResponse://HelpIQ_QnA`).

**Out of scope** (require closeout deliverable `multiplier-out-of-scope.md` per draft):

- On-behalf-of capture and beneficiary LDAP resolution
- License-tier matrix expansion (Salesforce, Tableau, Adobe tiers)
- Bulk requests (N>1 users) detection and routing
- Catalog-miss "Other" structured intake path
- Reasoning-trajectory LLM-as-judge rubric program (deferred from the 2026-05-13 draft variant)
- Router miss / welcome-message fallback (~22% — cross-cutting platform issue, separate ticket)
- KB ingestion lag (~1 week sync — operational pipeline)
- Catalog source-of-truth drift (needs canonical software catalog from SW Ops)
- Multi-language support
- Multi-turn deterministic runner (build cost outweighs current value)
- Geo / role pre-screen (e.g., "are you in Japan?" for Concur)

## Acceptance intent

Direct from `multiplier-ticket-draft.md` (7 ACs). Stored as `proposed` in `config.json` until Phase 3 checkpoint approval.

1. **Regression floor (blocking).** No multiplier-correctly-routed metric (coherence, completeness, conciseness, output_validation, action_completion completeness) drops more than 5pp vs the current Active version baseline on the existing 999-case Test Center suite. ±2pp counts as flat.
2. **Confirm-before-Submit (blocking).** Every Submit (`HelpIqAgentMultiplierSoftwareRequests`) invocation in multi-turn test scenarios is preceded by an accepted Confirm in a prior turn of the same conversation. 100% on multi-turn scenarios.
3. **Answer-vs-Submit classification (blocking).** Informational utterances reach Answer (not Submit); action-typed utterances reach Confirm-then-Submit. ≥80% on hand-authored multi-turn scenarios.
4. **Behavioral and catalog coverage (blocking).** Multi-turn set covers (a) all five Service Strategy buckets and (b) at least one example per behavioral category: multi-license/tier, qualifier-disambiguation, multi-option retrieval, auto-provisioned (Answer path), straightforward action (Confirm + Submit). At least 8 distinct catalog apps overall.
5. **GATHER tool-call correctness (blocking).** When GATHER fires for a catalog app, the agent calls `HelpIqAgentApplicationAccessDetails` with an `applicationKey` matching the user's intended app. No internal keys leaked in user-facing output. ≥90% on multi-turn scenarios that reach GATHER.
6. **GATHER-informed Clarify (non-blocking).** When retrieval returns multi-option results, the next Clarify uses those options rather than defaulting. ≥70% on hand-authored multi-option scenarios. Flag failures, don't gate close.
7. **Determinism / repeatability (blocking).** A representative subset of multi-turn scenarios (5–7) is run N=3 times; same Service Strategy classification + same slot summary on the Confirm turn across runs. ≥90% same-classification + ≥85% same-slot-summary. This tests whether structural primitives (vs prompt-only narrative) are doing their job.

## Versioning / edit strategy (Phase 2 confirmed)

- **Source of truth:** `force-app/main/default/aiAuthoringBundles/HelpIQ_AgentScript/HelpIQ_AgentScript.agent` (pro-code Agent Script bundle). No UI-built exception path — Phase 3a confirmed the only `GenAiPluginInstructionDef` wired to the v7 multiplier plugin is the **global** system instruction, not topic instructions; topic `reasoning.instructions` live in the `.agent` source.
- **Active baseline:** **v7** (BotVersion Id `0X9Em0000003HltKAE`, created 2026-05-14, model `sfdc_ai__DefaultGPT52`).
- **New BotVersion** to be cloned from v7 at the start of Phase 4/5, seeded with the current local `.agent` content (39,183 bytes, v7-equivalent per registry; multiplier topic block at lines 261–313 of the local file, byte-equivalent to v7 per `sf agent validate` success).
- **All iteration** happens against the new BotVersion (not the editable DRAFT bundle, not v7 Active).
- **Publish path.** Follow `developing-agentforce` upstream skill. **Known blocker:** orphan `GenAiPlannerDefinition` records for v4, v6, **v8** exist in the org as of Phase 3a (2026-05-16); v8 specifically blocks `sf agent publish authoring-bundle` because CLI naively picks "next version = v8" and conflicts. Expected resolution: user clones v7 in Studio (Studio's version-increment mechanism can skip reserved/orphan numbers and create v9 directly) or Salesforce admin clears orphans via Setup UI.

## HITL gates (Phase 4–5)

1. **End of Stage 0** — structural design (`eval/agent-script-design.md`) review before any prompt text is drafted.
2. **After first sandbox test run** — confirm `simulate-actions` behavior is acceptable and no real JSM tickets are filed; adjust Submit-safety strategy if needed (live + tagged, dry-run flag if discovered).
3. **End of Stage 1** — final eval + acceptance (publish/activate the new BotVersion only after approval).

## Eval / utterances

- **Regression suite:** Existing 999-case Test Center suite from HELPEXP-274. Suite API name to be confirmed at start of Phase 5 baseline run (registry mentions `HelpIQ_GPT52_v7_baseline_5_14_1`).
- **Multiplier baseline utterances:** `adlc/agents/HelpIQ_AgentScript__aicommon/baselines/HelpIqAgentMultiplierSoftwareRequests/utterances.txt` — 109 unique utterances built 2026-05-13 (27 tagged-multiplier + 58 software-access-category + 24 JSM supplemental).
- **Existing multi-turn fixtures:** 4 SW-ACCESS YAMLs at `baselines/.../scenarios/` (Figma happy path, Zoom multiple access, vague start, unsupported app). Reusable as starting point but use `simulator_rules` format, not the new scripted-variation format — Phase 3c will assess whether to adapt or replace.

## Submit safety during iteration (Phase 2 confirmed)

Default: `sf agent preview --simulate-actions` for all iteration runs. Phase 3a will probe whether `flow://HelpIqAgentMultiplierSoftwareRequests` has a dry-run flag (deferred to Phase 5 — not blocking for discovery). HITL gate #2 (after first sandbox test run) reconsiders.

## Prior HITL context

From `tickets/HELPEXP-274-generalqna-phased-prompt/hitl.jsonl` — 19 entries scanned. Most relevant for HELPEXP-286:

- **Slot template beats countable rule** (2026-05-09T19:35Z) — "structural/slot prompts beat countable rules for shape compliance on GPT 5.2 — give the model places to PUT things, don't just tell it what NOT to do." Directly relevant to designing the Confirm slot summary and Service Strategy classification.
- **Debug record accuracy gap** (2026-05-09T20:00Z) — "treat Debug as EVIDENCE, not GROUND TRUTH — always cross-check against actual reply body and tools-called list." Critical for AC #2 / AC #3 — we cannot trust the Debug self-report alone; rubric grading must verify against actual tool calls in trace.
- **Trace reveals markdown stripping at planner step** (2026-05-09T20:10Z) — Salesforce planner normalizes user-facing output. For prompt-compliance debugging, inspect `.sfdx/agents/<agent>/sessions/<sid>/traces/<traceId>.json` LLM raw output, NOT the rendered message. Applies to all rubric grading in Phase 5.
- **KB non-determinism dominates small batteries** (2026-05-09T19:50Z) — 4-utterance batteries too small; need 50+ utterance evals. Our 10–15 multi-turn scenarios @ N=3 = 30–45 runs which addresses this for Multiplier rubric metrics, plus the 109-utterance regression suite covers single-turn population.
- **CLI version sensitivity** (2026-05-09T19:15Z) — Studio/CLI feature divergence resolved by CLI upgrade in past. Check CLI version (`sf --version`) before any model_config or new syntax change.
- **Org auth as Phase 3a blocker** (2026-05-08T21:05Z–2026-05-09T00:00Z) — already cleared for this session (aicommon Connected per `sf config get target-org`).

## Open verification gap

The 2026-05-15 registry entry claims the multiplier topic block has sha256 `25d78a0c22bd632d` (first 16 chars) and 3708 chars. Phase 3a's hash of local file lines 261–313 produced `dbe8c227297141cc...` — different boundary (registry hash was likely of the `reasoning.instructions` body only, mine includes description + actions wiring). Not a drift indicator — `sf agent validate` passes and the structural content matches the legacy prompt documented in `multiplier-current-state.md` §1.2. Recorded as a verification caveat in `hitl.jsonl`.

## Pointers

- Ticket draft (authoritative scope): `../../multiplier-ticket-draft.md`
- Pre-ticket evidence brief: `../../multiplier-current-state.md`
- Discovery transcript (2026-05-13): `../../multiplier-discovery-transcript.md`
- Heavier draft variant (NOT canonical; rubric-judge program superseded): `../../multiplier-ticket-jira-ready.md`
- Sibling ticket: `../HELPEXP-274-generalqna-phased-prompt/`
- Multiplier baseline: `../../baselines/HelpIqAgentMultiplierSoftwareRequests/`
- Local `.agent` file: `/Users/obguzman/agentforce-project/force-app/main/default/aiAuthoringBundles/HelpIQ_AgentScript/HelpIQ_AgentScript.agent`
- Version registry: `../../AGENT_VERSION_REGISTRY.md`
- Architecture playbook: `adlc/playbooks/agentforce-architecture-playbook.md`
- Prompt engineering playbook: `adlc/playbooks/prompt-engineering-playbook.md`
- Core process overlay: `adlc/docs/core-process-overlay.md`
