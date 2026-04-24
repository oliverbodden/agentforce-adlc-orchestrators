# Internal Ticket Rewrites

> These are INTERNAL rewrites of existing ESCHAT tickets to test how well adlc-drive would handle them if properly structured. Not submitted to JIRA.

---

## ESCHAT-1178: JP ESA Locale Configuration
**Original problem:** Barely any structure. Mentions people, asks for Apex changes, but no clear agent/topic scope or acceptance.

### Rewritten:

**Title:** ADLC - Configure JP ESA Locale and Communication Interfaces

**Context:** JP ESA needs to send requests with `communicationLocale = "ja"` and support both `IndeedServiceChatbot` and `DradisIndeedMessage` communication interfaces for correct policy guidance.

**Requirements:**
1. Update Apex integration to request both communication interfaces in a single `jobPostStatuses` call
2. Set `communicationLocale = "ja"` for JP ESA requests
3. For each returned messaging tag, prefer `IndeedServiceChatbot`; fall back to `DradisIndeedMessage` if absent

**Agent:** JP ESA (API name: TBD — needs discovery)
**Org:** TBD
**Acceptance:**
- JP ESA returns Japanese-locale policy guidance in responses
- Fallback logic works when `IndeedServiceChatbot` message is absent
- No regression on existing JP ESA functionality

**adlc-drive assessment:** This is Apex/Flow work, not instruction editing. Drive would flag this as out of scope for instruction optimization and suggest using `adlc-scaffold` or manual Apex development instead.

---

## ESCHAT-1151: Permissions API Investigation
**Original problem:** Investigation ticket with data but no structure for drive.

### Rewritten:

**Title:** [SPIKE] Investigate Permissions API behavior for hidden accounts and secondary users

**Context:** The Permissions API returns unexpected data for hidden accounts (noreply-XYZ@hidden.indeed.com) and secondary users, causing ESA to fail when looking up account data.

**Questions:**
1. What does the Permissions API return for hidden accounts vs primary users?
2. How should ESA handle secondary users who are the actual operators?
3. What's the volume of sessions affected by these permission mismatches?

**Agent:** Indeed Service Agent (`Agentforce_Service_Agent`)
**Time-box:** 3 days
**Output:** Findings document with recommendations for instruction/action changes

**adlc-drive assessment:** SPIKE — drive would output an investigation plan using `adlc-optimize` Phase 1 (session trace analysis) to quantify the impact, then produce a findings document.

---

## ESCHAT-1149: ESA Data Access Failures
**Original problem:** Investigation with a data table but no requirements or acceptance.

### Rewritten:

**Title:** [SPIKE] Root cause analysis of ESA data access failures (Permission/Credential errors)

**Context:** ESA fails to access data in some sessions due to Permission/Credential errors between Salesforce, MuleSoft, and OneGraph.

**Questions:**
1. What's the volume of affected sessions?
2. Root cause: token acquisition failure, MuleSoft error, OneGraph issue, or other?
3. Which topics are most affected?
4. Can we add error handling instructions to gracefully handle these failures?

**Agent:** Indeed Service Agent (`Agentforce_Service_Agent`)
**Time-box:** 5 days
**Output:** Root cause breakdown with volume data + recommendation (instruction change vs infrastructure fix)

**adlc-drive assessment:** SPIKE — drive would pull STDM session data via `adlc-optimize` to quantify and categorize failures, then recommend whether the fix is instruction-level (add error handling guidance) or infrastructure-level (fix credentials).

---

## ESCHAT-1140: Section-Aware Chunking with Overlap
**Original problem:** POC/analysis ticket with business context but no agent scope or acceptance.

### Rewritten:

**Title:** [SPIKE] Evaluate section-aware chunking with overlap for RAG retrieval improvement

**Context:** ESA's RAG doesn't consistently retrieve full contextual sections from knowledge articles. This results in partial answers and missed guidance. A prior SPIKE (section-aware chunking without overlap) was completed.

**Questions:**
1. Does adding overlap between chunks improve retrieval completeness?
2. What's the optimal overlap size for ESA's knowledge articles?
3. How does this affect latency and token consumption?
4. Does response quality improve measurably vs current chunking?

**Agent:** Indeed Service Agent — GeneralFAQ topic (primary RAG consumer)
**Org:** devesa3
**Time-box:** 5 days
**Output:** Comparative analysis (current vs overlap chunking) with eval results

**adlc-drive assessment:** SPIKE with eval component — drive would set up a baseline eval on current RAG quality, then compare against the overlap chunking configuration. Not an instruction change but uses the eval framework.

---

## ESCHAT-1117: Ensure "Representative" Consistency
**Original problem:** One sentence, no structure. Now redundant with ESCHAT-1192.

### Rewritten:

**Title:** ADLC - Standardize "representative" terminology across all ESA topics

**Context:** ESA inconsistently uses "specialist", "agent", and "representative" when referring to human support. Should always be "a representative."

**Requirements:**
1. Audit all topic instructions for instances of "specialist", "agent", "our service representative"
2. Replace all with "a representative"
3. Include in global instructions to prevent future drift

**Agent:** Indeed Service Agent (`Agentforce_Service_Agent`)
**Topics:** All — global instruction + each topic
**Acceptance:**
- Zero instances of "specialist" or "agent" (when referring to human support) in any response
- Eval: 100% of escalation responses use "representative"

**Baseline:** Current eval CSVs — grep for terminology usage

**adlc-drive assessment:** Simple instruction fix. Drive would audit all instruction records, make surgical replacements, and verify via eval. Low risk. **NOTE: Now covered by ESCHAT-1192 — recommend closing as duplicate.**

---

## ESCHAT-1083: Incorporate Official Content Guidelines
**Original problem:** Empty description.

### Rewritten:

**Title:** ADLC - Implement official content guidelines across ESA agents

**Context:** [NEEDS INPUT] What are the official content guidelines? Link to doc or paste guidelines here.

**Requirements:**
[NEEDS INPUT] — Cannot write requirements without knowing what the guidelines say.

**adlc-drive assessment:** Cannot execute. Needs a SPIKE first to identify what the guidelines are, or the author needs to attach/link the guidelines document. **Recommend: either attach the guidelines and convert to an implementation ticket, or convert to SPIKE.**

---

## ESCHAT-1082: Show/Hide Toggle for Additional Details
**Original problem:** Just a screenshot and one sentence about progressive disclosure.

### Rewritten:

**Title:** ADLC - Implement progressive disclosure (show/hide) in ESA responses

**Context:** Long ESA responses could benefit from progressive disclosure — showing a summary first with an option to expand for details.

**Requirements:**
[NEEDS INVESTIGATION]
1. Does the messaging channel (Scout/chat) support expandable sections or show/hide UI?
2. If not, can we simulate progressive disclosure with "Would you like more details?" follow-up pattern?
3. Which topics have responses that would benefit? (likely Invoice Inquiries with long breakdowns)

**adlc-drive assessment:** Needs SPIKE first. The "show/hide" might be a UI/channel capability question, not an instruction change. If the channel supports it, this becomes an instruction change to structure responses with summary + details. If not, it's a conversation design change (ask before showing details). **Recommend: convert to SPIKE.**

---

## ESCHAT-1165: Knowledge Article Syncing in QA
**Original problem:** Process/infrastructure question, not an agent change.

### Rewritten:

**Title:** Establish process for knowledge article syncing between production and QA

**Context:** Content team needs to edit knowledge articles in QA and test ESA impact. ESA team needs ability to test with production-only articles. Other teams face similar needs.

**Requirements:**
1. Define sync process: one-way (prod→QA) or two-way
2. Determine if dynamic retrievers work correctly in QA (open case: 473045810)
3. Align with other teams using knowledge retrieval in QA

**adlc-drive assessment:** Infrastructure/process ticket, not instruction editing. Drive cannot execute this — it's about Data Cloud configuration and knowledge management, not agent instructions. **Recommend: keep as manual process ticket.**

---

## ESCHAT-1124: Invoice Response Formatting
**Original problem:** Has specific before/after examples but no acceptance criteria or agent reference.

### Rewritten:

**Title:** ADLC - Update Invoice response formatting (bold values, link style)

**Context:** Invoice Inquiries responses need formatting cleanup per UXCD review.

**Requirements:**
1. Bold VALUES not labels: `Due Date: **[dueDate]**` not `**Due Date:** [dueDate]`
2. Bold invoice total: `**[currencySymbol][amount]**`
3. Remove "here" from download links — use descriptive text
4. Add currency formatting: always 2 decimals with commas

**Agent:** Indeed Service Agent (`Agentforce_Service_Agent`)
**Topic:** Invoice Inquiries (`Invoice_Inquiries_16j770ab13ee312`)
**Acceptance:**
- Bold applied to values in >90% of responses
- No "here" link text in any response
- Currency always formatted with 2 decimals

**Baseline:** `adlc/indeed-service-agent/baselines/v21/`

**adlc-drive assessment:** Good candidate. Surgical instruction edit — modify the template formatting rules in the Invoice instruction. Low risk. **NOTE: Some of these may now be covered by ESCHAT-1192 — check for overlap.**

---

## ESCHAT-1115: Update Named Credentials for MuleSoft
**Original problem:** Infrastructure ticket about credential configuration, not agent instructions.

### Rewritten:

No rewrite needed — this is not an adlc-drive ticket.

**adlc-drive assessment:** Infrastructure/DevOps work. Named credentials are Salesforce configuration, not agent instructions. **Drive would immediately flag this as out of scope.**

---

## ESCHAT-1114: Recreate Knowledge Data Streams in DEVESA3
**Original problem:** Infrastructure ticket about Data Cloud data streams.

### Rewritten:

No rewrite needed — this is not an adlc-drive ticket.

**adlc-drive assessment:** Data Cloud infrastructure setup. **Drive would immediately flag this as out of scope.**

---

## Summary: Gaps Identified

| Gap | Tickets affected | Fix needed |
|---|---|---|
| **Drive needs to detect out-of-scope tickets** — infrastructure, Apex, Data Cloud config are not instruction edits | ESCHAT-1178, 1115, 1114, 1165 | Drive Phase 1 should classify: "Is this an instruction/prompt change, or infrastructure?" and flag non-instruction work early |
| **Empty/vague tickets need SPIKE conversion** | ESCHAT-1083, 1082 | Drive should detect near-empty tickets and suggest converting to SPIKE |
| **Duplicate detection** | ESCHAT-1117 (covered by 1192) | Drive should search for related tickets before starting |
| **Formatting-only tickets overlap with tone tickets** | ESCHAT-1124 partially covered by 1192 | Drive should flag potential overlap with in-progress tickets |
