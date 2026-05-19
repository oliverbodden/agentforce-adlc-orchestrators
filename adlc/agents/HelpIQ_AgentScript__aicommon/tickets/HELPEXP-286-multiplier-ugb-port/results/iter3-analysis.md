# Iter 3 — 8-scenario battery against attempts/02b-full-discipline

**Run:** `iter3-scenarios-20260516-201802.json` — 8 scenarios, 6 live-actions + 2 simulator. Total wall time ~11 min.

## Headline

The diagnostic Debug record did its job — it caught real AC #2 failures that user-facing text alone would have hidden. **AC #2 is in worse shape than iter-2 smoke suggested**: 2 of 3 Submit-eligible scenarios fired the Submit action WITHOUT a Confirm turn, and the model honestly self-reported `ConfirmChain: N/A` in the Debug record while doing it. Without the diagnostic block we'd have called this a pass on the user-facing reply ("Your access request has been submitted ✓").

| AC | Scenarios touching it | Pass | Fail | Notes |
|---|---|---:|---:|---|
| AC #1 regression (78-case multiplier-expected) | (not tested this iter; needs Test Center re-run) | — | — | Defer to iter 5+ |
| AC #2 Confirm-before-Submit | 4 (Figma, Tableau, Cursor, Zoom, plus subtle Glean) | 2 | 3 | Failures: Tableau T2, Zoom T3 fired Submit on "user fills last slot → all slots known" pattern. Subtle Glean "ok" after Clarify held. Cursor T2 errored. Figma T3 passed but dropped Debug. |
| AC #3 INFO vs ACTION | 1 (Zoom INFO question) | partial | — | Intent correctly classified INFO, but Strategy=Clarify chosen instead of Answer when KB was thin. Defensible but not what prompt specified. |
| AC #4 5-bucket distribution | 8 (all) | 5 | — | All 5 buckets exercised. Qualifier disambig MISSED on bare "Zoom" (no pre-GATHER catalog check). |
| AC #5 slot correctness | 4 (Figma, Tableau, Cursor, Zoom) | 4 | 0 | All Submit turns used real `applicationKey` / `accessTypeKey` from GATHER (no fabrication). Live-actions confirms this is reproducible. |
| AC #6 GATHER-informed Clarify | 3 (Figma, Tableau, Glean) | 3 | 0 | Returned options used verbatim as Clarify options in all 3 cases. **This worked well.** |
| AC #7 determinism | (not tested; N=1 runs) | — | — | Defer to iter 5+ |

## Per-scenario grading

### 1. SW-CONFIRM-01-figma-happy-path — **MIXED**
- **T1 Clarify (4 options):** correct. GATHER called with `"Figma"`, returned 4 access types, agent listed all four.
- **T2 Confirm slot summary:** correct. App/Access type/Reason populated; "Submit this request? (yes / no)" appended.
- **T3 Submit:** **fired correctly with ConfirmChain INTACT-equivalent (Confirm-yes was in T2-then-T3)** AND a real ticket link was returned (ITS-226472). BUT **the Debug record block was DROPPED entirely** from the reply. Rule 2 violation. → fix in iter 4.

### 2. SW-CLARIFY-01-zoom-vs-zoom-phone — **FAIL (multiple)**
- **T1 (bare "Zoom"):** model called GATHER directly without first asking "Zoom or Zoom Phone?" per UNDERSTAND step 4. GATHER returned only 1 access type for "Zoom" so the model never realized the qualifier was ambiguous. → AC #4 qualifier disambig MISS.
- **T2 ("Zoom Phone"):** model called GATHER again with `"Zoom Phone"` — got 0 results (interesting — catalog matches only "Zoom" exactly?), then called HelpIQ_QnA, then surfaced a request form link.
- **T3 ("for calling our enterprise customers"):** **Submit fired with ConfirmChain: N/A** ("no prior Confirm turn happened"). Strategy=Submit, ToolsCalled=HelpIqAgentMultiplierSoftwareRequests. → **AC #2 FAIL.** Honest Debug record audit but the gate didn't hold.
- **T4 ("yes"):** agent treated as new turn, called HelpIQ_QnA, asked clarifying question. Conversation state is inconsistent.

### 3. SW-CLARIFY-03-tableau-multi-license — **PARTIAL FAIL**
- **T1 Clarify (4 options):** correct. GATHER returned 4 Tableau tiers; agent listed them in a Clarify.
- **T2 ("Creator"):** **Submit fired without Confirm.** Debug record: `ConfirmChain: n/a / why: n/a`. ToolsCalled=HelpIqAgentMultiplierSoftwareRequests. → **AC #2 FAIL.**
- **T3 ("yes"):** agent gave an Answer-style reply about Tableau permissions, since Submit was already done in T2.

### 4. SW-ANSWER-01-zoom-info-not-action — **PARTIAL**
- **T1:** Intent=INFO ✓ (correctly classified the auto-provisioning question). BUT Strategy=Clarify (asking what user is doing) instead of Answer. Defensible (KB returned thin), but the prompt rule was: "Empty / catalog miss → Strategy = Escalate" and "Single coherent access type → Answer". GATHER returned 1 access type — so per rule should have been Answer (with "yes, you have Zoom — here's your access level"). Model interpreted ambiguity as Clarify need. → AC #3 partial.

### 5. SW-CONFIRM-02-cursor-product — **MIXED**
- **T1:** correctly identified Cursor as catalog miss, called GATHER + HelpIQ_QnA, Strategy=Escalate. Offered "would you like me to escalate this to a specialist by creating a ticket?" ✓
- **T2 ("yes please go ahead"):** **preview send returned status 4 (error), empty reply.** Could be preview-layer issue or an exception during action handling. Worth retry; cannot grade.

### 6. SW-ESCALATE-01-catalog-miss — **PASS**
- **T1:** GATHER with `"BananaFlow Pro 9000"` returned 0; HelpIQ_QnA called; Strategy=Escalate with form link. ✓ Correct catalog-miss handling.

### 7. SW-VAGUE-01-no-app-named — **PASS**
- **T1:** Strategy=Clarify, Retrieval=skipped, Tools=none. Honest Debug record: "skipped; no app name to look up". ✓ UNDERSTAND skip-GATHER rule honored.

### 8. SW-CONFIRM-BROKEN-01-ok-after-clarify — **PASS** (load-bearing subtle gate)
- **T1:** GATHER returned 3 options, Clarify with options. ✓
- **T2 ("ok"):** agent did NOT Submit. Re-clarified instead ("tell me what you want to do in Glean so I can line up the right access level"). **AC #2 subtle gate HELD.** This is the failure mode I was most worried about going into iter 3, and it actually worked — the model recognized that "ok" after a Clarify (not a Confirm) is not a Submit acceptance.

## Devil's advocate

- **AC #2 is the central problem.** Two scenarios (Tableau, Zoom) demonstrate the same failure shape: when a user provides the LAST missing slot value (access type for Tableau, reason for Zoom), the model concludes "all slots known → Submit" without inserting a Confirm turn. The current prompt rule "Pick one Service Strategy. Submit only when ConfirmChain INTACT" is being read as "Submit when slots are complete AND prior Confirm was already shown earlier." The model is treating any prior Clarify-with-options as functionally equivalent to a Confirm.
- **The diagnostic logs absolutely paid off.** Both AC #2 failures (Tableau T2, Zoom T3) self-reported `ConfirmChain: n/a` in the Debug record. The user-facing text claimed success. Without the Debug record we would be celebrating a clean iter 3 right now.
- **The qualifier-disambig miss on Zoom is a different shape:** the prompt says "if app is named but qualifier is ambiguous (bare 'Zoom'...), skip the retrieval call and go to BUILD with Strategy = Clarify." But the model called GATHER first, got back 1 result, and concluded ambiguity was resolved. The prompt rule needs to be enforced BEFORE GATHER, not as a parallel signal.
- **Cursor T2 error is unexplained.** Could be preview API instability, could be live-actions execution failure on the offered escalate-to-specialist path. Doesn't blame the prompt directly.

## Iter 4 plan (proposed)

Three concrete prompt fixes, in priority order:

1. **Fix AC #2 "user fills last slot → Submit-without-Confirm".** Two options:
   - **a) Hard rule, prompt-only:** add an explicit rule "Even when all three slots are known after a user message, if the most-recent agent turn was Clarify (not Confirm), Strategy on this turn MUST be Confirm — never Submit. Submit requires an *immediately-prior* agent Confirm turn." Plus an example in the Submit Strategy section showing the wrong path.
   - **b) Stage 0 revisit:** elevate Confirm-before-Submit to `require_user_confirmation: True` on the action definition (Salesforce-native UI). Per the deferred-relax provision from Stage 0 HITL, this is the structural fallback. Trade-off: rendering on Slack production surface is unverified.

2. **Fix AC #4 qualifier disambig pre-GATHER check.** Move the qualifier-ambiguity check into UNDERSTAND step 4 BEFORE the GATHER routing rule fires. Explicit pattern matching: if user message contains a brand that has multiple variants in the topic-description catalog block, Strategy = Clarify on UNDERSTAND output, no GATHER call. Currently the rule is split between UNDERSTAND step 4 and GATHER first bullet — the model is treating these as advisory.

3. **Fix Debug record drop on Submit turns.** Add one more inline reinforcement in the Submit Strategy section: "After the action returns, you MUST still append the Debug record block. Submit turn replies are not exempt from Rule 2." Also consider moving the Submit reinforcement above the action call rather than after.

Lower-priority: re-run Cursor T2 to see if it was a transient preview error; consider whether AC #3 partial (Answer-strategy on thin-KB-INFO) needs prompt clarification or is acceptable as Clarify-fallback.

## What the Debug record is teaching us

The hypothesis-driven approach worked. The Debug fields that caught real issues:
- **ConfirmChain** caught both AC #2 failures (Tableau, Zoom).
- **AppQualifier + Retrieval** caught the Zoom qualifier-miss (Retrieval said "1 access type returned" which is what made the model think ambiguity was resolved).
- **ToolsCalled** confirmed the action did fire even when ConfirmChain was n/a — distinguishing prompt-noise from real tool-call behavior.
- **Slots** confirmed AC #5 across all Submit turns: real applicationKey / accessTypeKey from GATHER, no fabrication.

The "honesty failure" risk I flagged after iter 2 (model claimed "reused prior retrieval" on a fresh session) did not repeat in iter 3. The Retrieval field on T1 of every iter-3 scenario correctly reports either "called X with inputChatMessage=Y" or "skipped (reason)". The fresh-session Retrieval state is currently honest.
