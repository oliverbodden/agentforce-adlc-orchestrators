# HelpIqAgentMultiplierSoftwareRequests — Current-State Brief

**Status:** Pre-ticket evidence gathering. This file holds raw context (current behavior, eval evidence, open questions) so `adlc-ticket` and `adlc-drive` Phase 3 can work from data instead of guesses. Scope decisions and hypotheses live in the ticket itself, not here. Once a ticket key exists, this content seeds `tickets/{KEY}-…/discovery-context.md`.

**Author:** Composer (Claude Opus 4.7), 2026-05-13

---

## 0. TL;DR

**From the 2026-05-13 discovery session with Dario Sanchez (Support Ops / IAM bridge), Chris Bopp (HelpIQ internals), Oliver Bodden, and Anthony Miguel:**

1. **HelpIQ today submits a Multiplier ticket with only 3 fields: app ID + access key + reason.** The JSM portal it's mirroring captures more (license type, on-behalf-of, urgency, multi-user, business case) — confirmed by Chris: *"It's just getting the ID associated with the application being requested, and then one follow-up question, like, what's your reasoning?"*
2. **"On behalf of" is the most frequently-cited friction point.** When a manager asks for a teammate, HelpIQ submits as the requester → Multiplier auto-detects requester already has access → ticket has to be reopened and re-routed manually. Chris confirmed today's HelpIQ has *"no concept of request on behalf of."*
3. **License-type variance is uncaptured.** Adobe / Figma (viewer/editor/collaborator/developer) / Office have multiple license types in the JSM portal; HelpIQ doesn't ask, so automation either picks a default or falls back to manual. Backstage and others have no extra fields — variance is per-app.
4. **App disambiguation on chat is unverified.** Multiple apps share names (Tableau Japan / Tableau Scaled Ops / Tableau base; Adcentral variants). Chris: *"It might just pick the first one it pulls back. It doesn't narrow it down."* Dario reports the JSM portal has near-zero wrong-app rate (~5%) but that's a UI advantage chat doesn't have.
5. **Geo / role / approval gating is downstream of HelpIQ today.** Restrictions like "Concur is for Japan" or "Data Lake bulk needs the CDER team" are enforced by the application-owner approver, not by HelpIQ. The KB articles describe these but HelpIQ doesn't surface them pre-submit.
6. **Bulk requests (>1 user) cannot be automated.** Some apps allow manual bulk-add (Gong, Adobe); others (Data Lake) cannot. HelpIQ today has no bulk-detection.
7. **"Other" path exists** for apps not in the catalog. HelpIQ's current prompt catalog is partially out of sync with the JSM portal catalog (Dario: *"there was a list that was being kept, but I don't think it's very up to date anymore"*).

**From the 999-case eval run on the 32 multiplier-mapped utterances (HELPEXP-274):**

8. **The Multiplier topic was NOT touched in HELPEXP-274.** Its prompt is still the legacy Agentforce-era version (loud caps, "MANDATORY FIRST STEP", "FORBIDDEN", "SILENCER RULE").
9. **It regressed on response quality under GPT 5.2 + the new GeneralQnA prompt** vs Legacy v4 / GPT4 v1: coherence 67% vs 99%, conciseness 64% vs 82–85%, completeness 60% vs 85%.
10. **Welcome-message fallback hits this topic too** (e.g., `"I need an access to Waldo and Mechabugs"` returned the canned welcome message despite 4 tool calls).
11. **Action sequencing is messy** even when routing is right: only ~32% of multiplier cases produced the "clean" single-call pattern. 35% called `AccessDetails` then fell back to `HelpIQ_QnA`.
12. **Eval coverage is thin.** 32 multiplier utterances vs 420 GeneralQnA. **Zero cases test the actual `HelpIqAgentMultiplierSoftwareRequests` ticket-creation action** — all 32 expect `HelpIqAgentApplicationAccessDetails`.

---

## 1. What this sub-agent does today

**Topic:** `HelpIqAgentMultiplierSoftwareRequests` (label same; not snake_case)
**Description:**
> Handles software access requests for a specific catalog of approved applications: Adobe, Asana, Confluence Cloud, Figma, Gitlab Prod, Glean, Gong, Grammarly, Huddle, Keeper, Zoom, Windsurf, Waldo, Slack, Microsoft Office 365, Passport, Tableau, Salesforce, Ishbook, Agiloft, Indeed TV, Cursor, Claude Code, N8N Prod, Lucid Software, Seismic, DataLake, Mechabugs, Tableau – Scaled Ops Site, Logrepo, Canva, Cloudflare Management Console – SCIM, Flex – Tableau Cloud.

### 1.1 Where it lives

```text
force-app/main/default/aiAuthoringBundles/HelpIQ_AgentScript/HelpIQ_AgentScript.agent
  • topic HelpIqAgentMultiplierSoftwareRequests        — line 258
  • reasoning.instructions                             — lines 264–298
  • reasoning.actions (3 bindings)                     — lines 299–310
  • action defs (HelpIQ_QnA, HelpIqAgentApplicationAccessDetails,
                 HelpIqAgentMultiplierSoftwareRequests) — lines 313–420
```

The router that fans into it:

```text
agent_router.reasoning.instructions (lines 65–67):
  "If intent is software access/licensing, use go_to_HelpIqAgentMultiplierSoftwareRequests;
   otherwise use go_to_GeneralQnA_HelpIQ."
```

### 1.2 Current reasoning (verbatim outline)

```text
### 1. Validate the Application and Qualifier (MANDATORY FIRST STEP)
   - If qualifier detected (e.g., "Zoom Phone"):
       STOP ALL OTHER WORKFLOWS. Ask user "standard or qualified?".
       If qualified → HelpIQ_QnA → Step 3 escalation check.
       If standard → Step 2.

### 2. Fetch Application Access Details (Acknowledge and Pivot)
   PRIORITY: Always start with "I can definitely help you request access to [Application] right here!"
   Action: HelpIqAgentApplicationAccessDetails.
   2A. If user declines: pivot to HelpIQ_QnA + escalation check.
   2B. Multiple types: present and ask user to pick.
   2C. "Unspecified/None/Default": SILENCER RULE — never mention "not specified";
       call it "General"; either acknowledge user's reason or ask for one.

### 3. Handle Knowledge Search & Escalation (Fallback Only)
   For technical how-tos, teammate requests, or qualified apps from Step 1:
   HelpIQ_QnA + immediate escalation check.

### 4. Create the Software Request
   Only after applicationKey + accessTypeKey + reasonForAccess obtained:
   HelpIqAgentMultiplierSoftwareRequests action.

## Response Guidelines
   - Acknowledgment Rule (offer help before steps)
   - No Internal "Leaking"
   - No Meta-Commentary
```

### 1.3 Three actions wired here

| Action | Backing target | Purpose |
|---|---|---|
| `HelpIQ_QnA` | `generatePromptResponse://HelpIQ_QnA` | KB / Glean retrieval, same as GeneralQnA |
| `HelpIqAgentApplicationAccessDetails` | `flow://HelpIqAgentGleanSearch` | Glean lookup of access types/keys per app |
| `HelpIqAgentMultiplierSoftwareRequests` | `flow://HelpIqAgentMultiplierSoftwareRequests` | Actually creates the JSM ticket — needs `applicationKey`, `accessTypeKey`, `reasonForAccess` |

Worth knowing: there's no escalation action wired in this topic — it relies on `HelpIqAgentEscalateAction` only via global instructions / GeneralQnA.

---

## 2. How it performs today (evidence, not opinion)

All numbers from HELPEXP-274's 999-case run, filtered to the 32 utterances whose `Expected Subagent` = `HelpIqAgentMultiplierSoftwareRequests` (each utterance × ~3 trials → ~78 cases per run).

### 2.1 Pass rates per metric, per version (multiplier rows only)

| Metric | Legacy v4 | GPT4 v1 | GPT5 v3 (old prompt) | **GPT5.2 v4 (new GeneralQnA prompt)** |
|---|---:|---:|---:|---:|
| `topic_assertion` | 73% | 0%* | 77% | **82%** |
| `actions_assertion` | 60% | 82% | 77% | **82%** |
| `output_validation` | 38% | **67%** | 55% | 53% |
| `completeness` | 59% | **85%** | 62% | 60% |
| `coherence` | **99%** | **99%** | 78% | 67% |
| `conciseness` | 82% | **85%** | 65% | 64% |

*GPT4 v1 row at 0% on `topic_assertion` is almost certainly a routing/labeling artifact — the run pinned `subjectVersion=v1`, which probably had a different topic name, so assertion was wrong category. Treat that one cell as suspect.

**The uncomfortable read:**
- The "modern" stack (GPT 5.2 + new GeneralQnA prompt) is the **best** at routing/action sequencing on multiplier rows.
- It is **the worst** on response quality (coherence, conciseness, completeness, output validation), losing to a vintage GPT4 v1 baseline.
- Likely cause: HELPEXP-274 changed GeneralQnA's response shape (Service Strategy templates, Debug record), but the **Multiplier topic still runs the legacy prompt**, so on multiplier rows we get the new model interpreting an old, capitals-heavy, branchy prompt — and adding the Debug record into responses where the rubric doesn't expect it.

### 2.2 What the model actually does on multiplier rows (GPT 5.2 + new prompt)

| Action sequence (78 cases) | Count | Read |
|---|---:|---|
| `[HelpIqAgentApplicationAccessDetails, HelpIQ_QnA]` | 27 | Glean lookup, then falls back to KB — Glean returned nothing useful |
| `[HelpIqAgentApplicationAccessDetails]` | 25 | "Clean" intended pattern |
| `[HelpIQ_QnA]` only | 14 | Wrong topic (router miss) — never hit Glean |
| `[HelpIqAgentApplicationAccessDetails, HelpIqAgentMultiplierSoftwareRequests]` | 8 | Went all the way to ticket creation |
| Redundant `AccessDetails × 2..4` (with extra QnA) | 4 | Loops |

| Topic the model actually picked | Count |
|---|---:|
| `HelpIqAgentMultiplierSoftwareRequests` | 64 |
| `GeneralQnA_HelpIQ` | 14 (router miss, ~18%) |

### 2.3 Concrete failure samples (from the GPT 5.2 + new prompt run)

**Welcome-message fallback** — `"I need an access to Waldo and Mechabugs"`:
> Hi! I'm here to help you with any IT questions or issues you have. Ask me for help whenever you need.

The action sequence on those cases was `[AccessDetails, AccessDetails]` and `[AccessDetails ×4, HelpIQ_QnA]` — i.e., the agent did call tools, but the user-facing response collapsed to the welcome string. Same 22% bug class as HELPEXP-274.

**Catalog mismatch** — `"Requesting to create Google Suite credential for n8n workflow"`:
> Google Suite / Google Workspace isn't showing up as a requestable app in our catalog, so I can't submit an automated access request for it from here. The best next step is to get this in front of an IT specialist.

That response is reasonable — but the prompt's catalog includes "Microsoft Office 365" and "Slack" but not "Google Workspace", and it has no general fallback for catalog-misses besides "escalate." The eval rubric's expected answer here is a structured intake ("share requester / purpose / temporary? / approval?"), which the response doesn't match — hence completeness 60% on these cases.

**Loud directives produce stilted prose.** Sample output features the prompt's mandatory phrase verbatim:
> "I can definitely help you request access to [Application] right here!"

Coherence/conciseness suffer because that line is bolted on regardless of whether it makes sense (e.g., user asking about a service-account permissions issue, not a fresh access request).

### 2.4 Eval-coverage gaps

| Gap | Count | Implication |
|---|---:|---|
| Apps in the prompt catalog | 33 | — |
| Distinct products in eval master tagged Multiplier | 10 | ~70% of the catalog has zero eval coverage |
| Multiplier eval rows total | 32 (25 single-turn, 6 multi-turn, 1 JSM-derived) | Tiny vs 420 GeneralQnA rows |
| Eval rows whose `Expected Action` = `HelpIqAgentMultiplierSoftwareRequests` | **0** | The actual ticket-creation action is **never tested**. All 32 expect `HelpIqAgentApplicationAccessDetails`. |
| Apps in evals NOT in prompt catalog | DocuSign, FloQast, iDash, Terraform Enterprise, Google Workspace credentials, etc. | Untested escape paths |

Source: `tickets/HELPEXP-274-generalqna-phased-prompt/HelpIQ-Evals-Master-3_2026-05-09.csv`.

---

## 3. Domain context from discovery (2026-05-13)

Full transcript: `multiplier-discovery-transcript.md` (alongside this file).

### 3.1 The JSM "Request Access to Software" portal — the model HelpIQ is meant to mirror

The portal is the canonical software-access request flow. Dario walked through it:

1. **App selection.** User searches/picks from a curated list. There's an **"Other"** option for apps not in the list.
2. **Dynamic per-app fields.** The form below the app picker changes based on the chosen app:
   - **Adobe, Figma, Office** → license-type dropdown (Figma: viewer / editor / collaborator / developer)
   - **Backstage** → no extra fields
   - Some apps include an **urgency** field (Chris noted but not deeply explored)
3. **"Raise on behalf of"** — separate from the requester field. LDAP-resolved as you type (auto-suggest from Indeed's directory; contractors with Indeed accounts also resolve).
4. **Request details / business case** field — required for stricter apps (limited license pools, geo-restricted, etc.).
5. **Submission** creates a JSM ticket. Approval is owned by the application owner (Daryl Shaw owns Figma, etc.).
6. **Provisioning** is automatic when approved for "automated" apps; manual (tech queue) for the rest.

Dario, on the JSM portal's user-error rate: *"Saying 'I requested the wrong thing'? Rarely. Very low percent — probably below 5."* Two contributors to that low rate: clean UI, and ability to Slack a teammate before clicking.

### 3.2 What HelpIQ does today (per Chris, 12:33–13:32)

> **Chris:** *"The only follow-up question that would be asked in this scenario, if someone says 'hey, I want Figma', would be 'what's your reason for wanting Figma?'. So it goes out and says, okay, they're asking for Figma. It basically does a lookup to get the access key, and so then it has Figma and the access key and the reason it's being requested, and it goes out and creates the JSM multiplier."*

Concretely, today's chat flow on a software-access request:
1. User mentions an app.
2. HelpIQ calls `HelpIqAgentApplicationAccessDetails` (Glean lookup) to get the access key.
3. HelpIQ asks one follow-up: *"What's your reason?"*
4. HelpIQ calls `HelpIqAgentMultiplierSoftwareRequests` with `{applicationKey, accessTypeKey, reasonForAccess}`.

Chris explicitly: *"I don't think it gets into any of that today."* — referring to license-type variance, urgency, on-behalf-of, environment, multi-user, etc.

### 3.3 Gaps named in the session

| Gap | Source / quote | Frequency Dario implied |
|---|---|---|
| **No on-behalf-of capture** | Chris (25:13): *"Today there's no concept of request on behalf of. It just populates 'raise on behalf of'."* | Dario: *"We see this happen very often … one of those issues we usually have here and there."* Frequent. |
| **No license-type capture** | Chris (12:33): listed urgency / variance as *"any of that"* HelpIQ doesn't capture. | Affects Adobe, Figma, Office, others — significant subset of the catalog. |
| **No urgency capture** | Chris (13:19): *"I saw an urgency field."* | Unknown. |
| **No business-case follow-up beyond "what's your reason"** | Chris (13:32): *"one follow-up question, like, what's your reasoning."* | Stricter apps (limited license pools, geo-gated) need more. |
| **No app disambiguation on chat** | Chris (24:55): *"It might just pick the first one it pulls back. It doesn't narrow it down."* Oliver (24:21): *"I don't have the data enough to know if it's a problem."* | Unknown — may be hidden by Dario's *"almost never"* portal-side number, which doesn't include chat-originated requests. |
| **No geo/role pre-screen** | Dario (19:30): Concur is *"primarily for Japan"*; restriction is enforced by the approver, not by HelpIQ. | Per-app — most apps have no restriction; a handful do. |
| **No multi-user / bulk detection** | Dario (16:30): Data Lake bulk-add request couldn't be done; some apps allow manual bulk, others can't. | Rare but visible (Dario cited a 20-person request from "a few days ago"). |
| **No catalog-miss handling beyond escalate** | Discovery + brief §1.2 — current prompt has no explicit "Other" pathway. | Catalog list is *"not very up to date anymore"* per Dario. |

### 3.4 Required behaviors and their information sources

Discovery surfaced concrete behaviors the agent needs to perform. The column below records **where the information lives** (user utterance vs external lookup), which informs but doesn't decide phase placement. Phase placement (UNDERSTAND vs GATHER) is prompt-design work and lives in `adlc-drive` Phase 4. Some behaviors span both phases.

| Behavior | Information source | Source quote / evidence |
|---|---|---|
| Identify the app from user input | User utterance | Implicit across discovery |
| Detect on-behalf-of phrasing | User utterance | Dario (14:28): *"I am a manager, I want to request this on behalf of my team..."* |
| Detect bulk (N>1 users) | User utterance | Dario (16:30): *"someone who came with a list of, like, 20 people"* |
| Extract business case if user volunteered one | User utterance | Chris (12:33) on today's single follow-up *"what's your reason?"* |
| Resolve beneficiary LDAP/email | External lookup (directory) | Dario (15:51): *"if you type right here, it's on the database already. It will pull my LDAP."* |
| Look up access details / license types | External lookup (`AccessDetails`) | Dario (05:45) on Adobe / Figma / Office license variants |
| Classify `AccessDetails` return → in-catalog vs "Other" | Tool return classification | Dario (26:51): *"Not all the apps are in here... that's why there is an Other"* |
| Disambiguate when name maps to multiple apps (Tableau ×3, Adcentral) | **User utterance + tool lookup** | Chris (24:55): *"It might just pick the first one it pulls back. It doesn't narrow it down."* |
| Surface geo/role restriction before submit (optional) | External lookup (KB article via `HelpIQ_QnA`) | Dario (19:30) on Concur Japan; Oliver (20:50) raised the *"are you in Japan?"* idea |
| Decide whether to call KB at all | Combined: utterance specificity + prior tool returns | GATHER routing — same shape as GeneralQnA's *"materially new question or follow-up"* rule |

**Two patterns to flag:**
- Behaviors sourced from user input fit naturally in UNDERSTAND parsing. Behaviors requiring external lookups fit naturally in GATHER. Behaviors needing both (disambiguation, on-behalf-of resolution) span phases — drive Phase 4 will need to plan the hand-off.
- **"When to call knowledge"** is GATHER's routing problem and is architecturally identical to GeneralQnA's existing rule: call when the question is materially new; reuse prior tool output when the user is clarifying or zooming. Multiplier extends this across two tools (`AccessDetails` and `HelpIQ_QnA`) instead of one.

### 3.5 Constraints worth knowing

- **LDAP resolution.** "Raise on behalf of" requires resolving a name → LDAP. HelpIQ today doesn't do this, but the data is in the user directory (contractors included). Whatever flow we add must be able to resolve a name to an Indeed account before submitting.
- **KB ingestion lag.** New / updated articles take ~1 week to appear in the retriever (Anthony confirmed it's a weekly sync, can be done ad-hoc on request). New apps and policy changes will not be visible to HelpIQ for up to a week. This affects any "find the article first" strategy.
- **Approval is downstream.** HelpIQ's job is to submit a clean, complete request — not to gate access. The application owner approves/denies. Don't confuse "good submission" with "access granted."
- **The catalog in the prompt vs the catalog in the JSM portal vs the catalog in Glean** are three things that may not be in sync (Dario, indirectly: *"there was a list … not very up to date anymore"*). A discovery action item: get the up-to-date list from the software team.
- **Oliver's stated intent** (25:44): *"I think that's gonna be something we'll have to add to the prompt. At least those high-level decisions, and then I'm also curious on request details, because that seems to be pretty critical for the creation of the automation. Those are two things — request on behalf of, asking discovery questions, hey, is this for you, for someone else?"*

---

## 4. Carry-overs from HELPEXP-274

Reusable assets and operational lessons that apply to this next ticket.

| Asset | Path | How it serves the next ticket |
|---|---|---|
| Phased-reasoning template | `tickets/HELPEXP-274-…/GENERALQNA_REASONING.md` | Reference structure (UNDERSTAND/GATHER/BUILD + Service Strategy + Debug record) |
| Eval master CSV | `tickets/HELPEXP-274-…/HelpIQ-Evals-Master-3_2026-05-09.csv` | Already has 32 multiplier rows tagged; we extend or enrich, don't rebuild |
| Eval pipeline scripts | `tickets/HELPEXP-274-…/build_eval_xml.py`, `build_eval_report.py`, `analyze_eval_results.py`, `spot_check_compare.py` | Reusable; just point at new spec name |
| HTML report generator | `build_eval_report.py` + `results/iteration_evaluation_report.html` | Already supports 4-version diff; add a 5th column for the Multiplier candidate |
| Version registry | `AGENT_VERSION_REGISTRY.md` | New runs go in the experiments table |
| Prompt-engineering playbook | `adlc/playbooks/prompt-engineering-playbook.md` | Lessons (loud directives, debug record, "minimum fix first") apply directly |
| Global rules | `adlc/docs/core-process-overlay.md` | Deploy-to-test, no commit until validated, avoid version inflation — all carry over |

**Operational carry-overs (from the last run's bruises):**
- Don't auto-publish; deploy + preview while iterating.
- **Always retrieve eval results before deleting the test definition** (we lost run #2 to this last time).
- CLI `/results` endpoint is *slow*, not broken — use `--wait 15` or higher.
- Studio UI's version display is unreliable; trust SOQL.
- HITL only on actual problems, not routine progress.
- Keep ticket folder file count low — last time it sprawled to a dozen MD files we couldn't navigate.

---

## 5. What's still open going into `adlc-ticket`

The 2026-05-13 discovery (§3) resolved most of the original open questions (problem framing, target mental model, the gap inventory). What's left as input for `adlc-ticket` Mode 1:

1. **Up-to-date catalog from the software team.** Dario flagged the existing catalog as stale; the prompt's catalog is hand-maintained. Need a current list of Multiplier-supported apps and which are automated vs manual.
2. **Chat-originated wrong-app rate.** Dario's *"below 5%"* figure is for the JSM portal where users can read disambiguating descriptions. We don't know the rate for HelpIQ, where users only type the app name. If meaningful, disambiguation belongs in scope.
3. **Whether to surface KB-derived restrictions pre-submit** (e.g., *"are you in Japan?"* for Concur). Oliver raised it as a "thinking out loud" idea; needs a product call given the ~1-week KB ingestion lag for new articles.
4. **Eval coverage for the ticket-creation path.** Currently zero eval cases exercise `HelpIqAgentMultiplierSoftwareRequests` directly. Adding coverage is a separate decision — could be its own ticket or bundled.
5. **Bulk-request behavior.** Should HelpIQ detect *"I need access for 20 people"* and route to a tech, attempt structured intake, or refuse? No precedent in current prompt or evals.
6. **Router miss + welcome-message fallback** — confirmed cross-cutting issues, not this topic's prompt. Worth tagging as *"out of scope, separate platform tickets"* in whatever this ticket becomes.

Scope decisions, hypotheses, and acceptance criteria live in the ticket itself, not here (see `adlc/playbooks/ticket-prep-playbook.md`).
