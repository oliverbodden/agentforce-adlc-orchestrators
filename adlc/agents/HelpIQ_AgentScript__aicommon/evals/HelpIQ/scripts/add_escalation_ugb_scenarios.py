#!/usr/bin/env python3
"""Add Escalation-UGB acceptance scenarios to the three eval masters.

- Rewrite dynamic `direct_human_yes_context` (button -> in-chat UGB clarify).
- Append 7 new dynamic scenarios (bare create/escalate, anti-repeat skip-clarify,
  frustration fast-track, turn-cap, urgency High, urgency Medium).
- Append multi-turn escalation rows with varied conversation histories.
- Append single-turn bare-intent regression guards.

Run from the evals/HelpIQ dir. Idempotent-ish: refuses to add a row id that already exists.
"""
from __future__ import annotations
import csv, json, sys
from pathlib import Path

BASE = Path(".")
DYN = BASE / "dynamic_tests.csv"
MULTI = BASE / "multi_turn_tests.csv"
SINGLE = BASE / "single_turn_tests.csv"

SRC_DEF = "adlc/agents/HelpIQ_AgentScript__aicommon/evals/HelpIQ/scripts/run_dynamic_tests.py"
QM = "expected_answer_alignment|completeness|coherence|conciseness"


def load(path):
    with path.open(newline="") as f:
        r = csv.DictReader(f)
        return list(r), r.fieldnames


def write(path, rows, cols):
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


# ---------------- DYNAMIC ----------------
dyn_rows, dyn_cols = load(DYN)

# 1) Rewrite the bare-human row: button -> in-chat UGB
for r in dyn_rows:
    if r["scenario_id"] == "direct_human_yes_context":
        r["summary"] = "Bare human request gathers the issue in chat (no button), runs intake discovery, confirms, then files only after yes."
        r["strategy"] = "bare_human_then_issue_then_submit"
        r["expected_behavior"] = ("Agent does NOT mention or offer any Talk to Live Agent button. It asks what the IT issue is, "
                                   "runs EscalationIntakeDiscovery, presents a standardized confirm summary ending in 'Want me to submit it?', "
                                   "and creates the IT ticket only after the user says yes, then closes without follow-up questions.")
        r["allowed_tools"] = "EscalationIntakeDiscovery|HelpIqAgentEscalateAction"
        r["forbidden_tools"] = "HelpIQ_QnA|HelpIqAgentMultiplierSoftwareRequests"
        r["tool_policy_notes"] = "No button. Clarify the issue, run intake discovery, then create the handoff ticket only after explicit submit confirmation."
        r["notes"] = "HELPEXP-453 UGB: bare-intent button removed; bare 'talk to a human' now gathers the issue in chat."

# New dynamic rows (mirror existing column set)
def dyn_row(**kw):
    base = {c: "" for c in dyn_cols}
    base.update({
        "product": "IT Support",
        "category": "Hardware / IT Support",
        "scenario_category": "human_handoff",
        "risk": "high",
        "runs": "3",
        "quality_metrics": QM,
        "source_definition": SRC_DEF,
        "requires_confirmation_before_tool": "true",
        "expected_topic": "Escalation",
        "allowed_topics": "Escalation",
        "topic_policy": "expected_topic_only",
        "topic_policy_notes": "Stays in Escalation through discovery + confirmation gating.",
    })
    base.update(kw)
    return base

new_dyn = [
    dyn_row(
        scenario_id="bare_create_ticket_no_context", subcategory="Bare Ticket Request",
        summary="'create a ticket' with no stated issue must clarify the issue first, not file blindly.",
        initial_utterance="create a ticket", strategy="bare_create_then_issue_then_submit",
        expected_behavior=("Agent does not create a ticket on turn 1 and does not offer a button. It asks what the IT issue is, "
                           "then after the user states it runs intake discovery, confirms, and files only after yes."),
        allowed_tools="EscalationIntakeDiscovery|HelpIqAgentEscalateAction",
        forbidden_tools="HelpIQ_QnA|HelpIqAgentMultiplierSoftwareRequests",
        tool_policy="human_handoff_gated",
        tool_policy_notes="Bare ticket ask with no issue: clarify first, then discovery + confirm before filing."),
    dyn_row(
        scenario_id="bare_escalate_no_context", subcategory="Bare Escalate Request",
        summary="'escalate this' with no stated issue must clarify the issue first.",
        initial_utterance="escalate this", strategy="bare_escalate_then_issue_then_submit",
        expected_behavior=("Agent does not create a ticket on turn 1 and does not offer a button. It asks what the IT issue is, "
                           "then runs intake discovery, confirms, and files only after yes."),
        allowed_tools="EscalationIntakeDiscovery|HelpIqAgentEscalateAction",
        forbidden_tools="HelpIQ_QnA|HelpIqAgentMultiplierSoftwareRequests",
        tool_policy="human_handoff_gated",
        tool_policy_notes="Bare escalate with no issue: clarify first, then discovery + confirm before filing."),
    dyn_row(
        scenario_id="bare_intent_with_context_skips_clarify", subcategory="Live Agent Handoff",
        scenario_category="direct_it_ticket_intake",
        summary="Human request that already includes the issue must NOT re-ask the issue (anti-repeat).",
        initial_utterance="I need to talk to someone, my laptop won't power on after a coffee spill",
        strategy="context_rich_then_submit",
        expected_behavior=("Because the issue and key context are already stated, the agent does NOT ask 'what's the issue'. "
                           "It runs intake discovery at most once, presents a confirm summary, and files only after yes."),
        allowed_tools="EscalationIntakeDiscovery|HelpIqAgentEscalateAction",
        forbidden_tools="HelpIQ_QnA|HelpIqAgentMultiplierSoftwareRequests",
        tool_policy="direct_it_ticket_intake_confirm",
        tool_policy_notes="Anti-repeat: context already supplied; skip the issue clarify and move toward confirm."),
    dyn_row(
        scenario_id="frustrated_repeat_fast_track", subcategory="Frustration Fast-Track",
        scenario_category="direct_it_ticket_intake",
        summary="When the user is frustrated and says they have no more info, agent stops asking and files with what it has.",
        initial_utterance="my laptop is broken, open a ticket", strategy="frustration_fast_track",
        expected_behavior=("After the user expresses frustration and says they have no more information, the agent stops asking "
                           "discovery questions and moves straight to the submit confirmation using what it already has, then files after yes. "
                           "It does NOT re-ask for details it was already told."),
        allowed_tools="EscalationIntakeDiscovery|HelpIqAgentEscalateAction",
        forbidden_tools="HelpIQ_QnA|HelpIqAgentMultiplierSoftwareRequests",
        tool_policy="direct_it_ticket_intake_confirm",
        tool_policy_notes="Frustration fast-track: do not interrogate; confirm + file with available context."),
    dyn_row(
        scenario_id="over_asking_turn_cap", subcategory="Turn Cap", risk="medium",
        scenario_category="direct_it_ticket_intake",
        summary="Agent must reach the submit confirmation within the turn cap (at most one focused question).",
        initial_utterance="my monitor is flickering and I want a ticket", strategy="turn_cap_confirm",
        expected_behavior=("Agent asks at most one focused question before presenting the submit confirmation. It does not "
                           "interrogate across multiple turns; after one detail it confirms and files on yes."),
        allowed_tools="EscalationIntakeDiscovery|HelpIqAgentEscalateAction",
        forbidden_tools="HelpIQ_QnA|HelpIqAgentMultiplierSoftwareRequests",
        tool_policy="direct_it_ticket_intake_confirm",
        tool_policy_notes="Turn cap: one focused question maximum before confirm."),
    dyn_row(
        scenario_id="frustrated_urgency_high", subcategory="Urgency Detection",
        scenario_category="direct_it_ticket_intake",
        summary="Frustration / urgency cues set ticket urgency to High in the ticket description (interim, text-only).",
        initial_utterance="This is the third time my laptop has died today and I am furious, just open a ticket NOW",
        strategy="urgency_high_submit",
        expected_behavior=("Agent detects frustration/urgency, includes an 'Urgency: High' line in the ticket description it files, "
                           "confirms, and submits only after yes. Does not over-ask given the urgency."),
        allowed_tools="EscalationIntakeDiscovery|HelpIqAgentEscalateAction",
        forbidden_tools="HelpIQ_QnA|HelpIqAgentMultiplierSoftwareRequests",
        tool_policy="direct_it_ticket_intake_confirm",
        tool_policy_notes="Interim urgency: High urgency carried as a text line in RequestDescription (no JSM priority field yet)."),
    dyn_row(
        scenario_id="calm_urgency_medium", subcategory="Urgency Detection", risk="medium",
        scenario_category="direct_it_ticket_intake",
        summary="No urgency cues -> ticket urgency defaults to Medium.",
        initial_utterance="When you get a chance, could you open a ticket for a spare laptop charger?",
        strategy="urgency_medium_submit",
        expected_behavior=("No frustration/urgency cues, so the agent files with 'Urgency: Medium' in the ticket description, "
                           "confirms, and submits only after yes."),
        allowed_tools="EscalationIntakeDiscovery|HelpIqAgentEscalateAction",
        forbidden_tools="HelpIQ_QnA|HelpIqAgentMultiplierSoftwareRequests",
        tool_policy="direct_it_ticket_intake_confirm",
        tool_policy_notes="Interim urgency: default Medium when no urgency cues."),
]

existing_dyn_ids = {r["scenario_id"] for r in dyn_rows}
added_dyn = [r for r in new_dyn if r["scenario_id"] not in existing_dyn_ids]
dyn_rows.extend(added_dyn)
write(DYN, dyn_rows, dyn_cols)
print(f"DYNAMIC: rewrote direct_human_yes_context; added {len(added_dyn)} rows -> total {len(dyn_rows)}")

# ---------------- MULTI-TURN ----------------
multi_rows, multi_cols = load(MULTI)
existing_multi_ids = {r["test_id"] for r in multi_rows}
# Find max case_number in fixed_multi_turn suite
maxnum = max((int(r["case_number"]) for r in multi_rows if r.get("case_number","").isdigit()), default=0)

def hist(*pairs):
    out = []
    for i,(role,msg) in enumerate(pairs):
        d = {"index": str(i), "role": role, "message": msg}
        if role == "agent":
            d["topic"] = "Escalation"
        out.append(d)
    return json.dumps(out)

def multi_row(n, **kw):
    base = {c: "" for c in multi_cols}
    base.update({
        "test_id": f"fixed_multi_turn-{n:04d}", "suite": "fixed_multi_turn", "case_number": str(n),
        "type": "", "product": "IT Support", "category": "Hardware / IT Support", "subcategory": "Live Agent Handoff",
        "expected_topic": "Escalation", "original_expected_actions": "['escalate_to_human']",
        "judge_metrics": "completeness|coherence|conciseness|output_latency_milliseconds",
        "source_definition": SRC_DEF, "requires_confirmation_before_tool": "true",
        "allowed_tools": "HelpIqAgentEscalateAction", "forbidden_tools": "",
        "tool_policy": "escalate_after_context_or_confirmation",
        "tool_policy_notes": "Escalation action valid only after enough context and explicit/continued handoff request.",
        "allowed_topics": "Escalation", "topic_policy": "expected_topic_only",
        "topic_policy_notes": "Use the expected topic from the canonical test row.",
        "notes": "HELPEXP-453 UGB escalation acceptance (varied history).",
    })
    base.update(kw)
    return base

new_multi = [
    multi_row(maxnum+1,
        utterance="actually just open a ticket for this",
        conversation_history_json=hist(("user","how do I connect to the VPN?"),
            ("agent","Here are the steps to connect to the VPN: open the GlobalProtect app, enter vpn.indeed.com, and sign in with Okta. Did this help?")),
        expected_answer="Here's the ticket I'll file:\n- Issue: VPN connection help\n- Details: user could not connect after KB steps\n\nWant me to submit it?",
        subcategory="Escalation after KB turn",
        tool_policy="direct_it_ticket_intake_confirm",
        tool_policy_notes="Mid-conversation escalation after a KB answer: discovery+confirm before filing.",
        allowed_tools="EscalationIntakeDiscovery|HelpIqAgentEscalateAction",
        forbidden_tools="HelpIqAgentMultiplierSoftwareRequests"),
    multi_row(maxnum+2,
        utterance="I already told you it's my laptop and I don't have any more information!",
        conversation_history_json=hist(("user","my laptop won't turn on, open a ticket"),
            ("agent","Got it — a laptop that won't power on. What have you already tried (charger, different outlet, holding power 30s)?")),
        expected_answer="Understood — I'll file it with what we have.\n- Issue: laptop won't power on\n- Details: user reports no additional info\n\nWant me to submit it?",
        subcategory="Frustration Fast-Track",
        tool_policy="direct_it_ticket_intake_confirm",
        tool_policy_notes="Frustration fast-track: stop asking, move to confirm with available context. No re-ask.",
        allowed_tools="EscalationIntakeDiscovery|HelpIqAgentEscalateAction",
        forbidden_tools="HelpIqAgentMultiplierSoftwareRequests",
        notes="HELPEXP-453 UGB: frustrated user must not be re-asked."),
    multi_row(maxnum+3,
        utterance="create a ticket",
        conversation_history_json=hist(("user","is the office open on Monday?"),
            ("agent","Yes, the office is open Monday 8am-6pm. Anything else I can help with?")),
        expected_answer="Sure — what's the IT issue you want the ticket for (for example: laptop, VPN, Okta/MFA, software access, hardware)?",
        subcategory="Bare Ticket Request mid-convo",
        expected_actions="[]", original_expected_actions="[]",
        tool_policy="human_handoff_gated",
        tool_policy_notes="Bare ticket ask with no issue: clarify the issue first, no tool this turn.",
        allowed_tools="", forbidden_tools="HelpIqAgentEscalateAction|HelpIqAgentMultiplierSoftwareRequests"),
    multi_row(maxnum+4,
        utterance="yes, submit it",
        conversation_history_json=hist(("user","my keyboard stopped working, I need a ticket"),
            ("agent","Got it — keyboard not working. Which office are you in so the right team gets it?"),
            ("user","NYC"),
            ("agent","Here's the ticket I'll file:\n- Issue: keyboard not working\n- Details: NYC office\n\nWant me to submit it?")),
        expected_answer="Submitted. <ticket-link | Ticket>. An IT specialist will continue from the ticket in this Slack thread.",
        expected_actions="['HelpIqAgentEscalateAction']",
        subcategory="Confirm acceptance after gather",
        tool_policy="escalate_after_context_or_confirmation"),
    multi_row(maxnum+5,
        utterance="it's a Dell at the NYC office, and I'm pretty frustrated this keeps happening",
        conversation_history_json=hist(("user","my monitor keeps flickering, open a ticket"),
            ("agent","Sorry about the flickering monitor. Which monitor and office is this so the right team can help?")),
        expected_answer="Here's the ticket I'll file:\n- Issue: monitor flickering (Dell, NYC)\n- Urgency: High\n\nWant me to submit it?",
        subcategory="Urgency Detection (High)",
        tool_policy="direct_it_ticket_intake_confirm",
        tool_policy_notes="Frustration cue -> Urgency High carried in ticket description (interim).",
        allowed_tools="EscalationIntakeDiscovery|HelpIqAgentEscalateAction",
        forbidden_tools="HelpIqAgentMultiplierSoftwareRequests",
        notes="HELPEXP-453 UGB: sentiment -> urgency High."),
    multi_row(maxnum+6,
        utterance="I need to speak with a person about my Okta lockout",
        conversation_history_json=hist(("user","hi"),
            ("agent","Hi! I'm here to help with IT questions or issues. What do you need?")),
        expected_answer="Here's the ticket I'll file:\n- Issue: Okta account lockout\n- Details: user requests human help\n\nWant me to submit it?",
        subcategory="Bare intent + issue in one message (anti-repeat)",
        tool_policy="direct_it_ticket_intake_confirm",
        tool_policy_notes="Issue already stated with the human request: do not re-ask the issue.",
        allowed_tools="EscalationIntakeDiscovery|HelpIqAgentEscalateAction",
        forbidden_tools="HelpIqAgentMultiplierSoftwareRequests"),
]
added_multi = [r for r in new_multi if r["test_id"] not in existing_multi_ids]
multi_rows.extend(added_multi)
write(MULTI, multi_rows, multi_cols)
print(f"MULTI: added {len(added_multi)} rows -> total {len(multi_rows)}")

# ---------------- SINGLE-TURN ----------------
single_rows, single_cols = load(SINGLE)
existing_single_ids = {r["test_id"] for r in single_rows}
smax = max((int(r["case_number"]) for r in single_rows if r.get("case_number","").isdigit()), default=0)

def single_row(n, utt, ans, sub):
    base = {c: "" for c in single_cols}
    base.update({
        "test_id": f"single_turn-{n:04d}", "suite": "single_turn", "case_number": str(n),
        "type": "Single-turn fixed utterance", "product": "IT Support",
        "category": "Hardware / IT Support", "subcategory": sub,
        "utterance": utt, "conversation_history_json": "[]",
        "expected_topic": "Escalation", "expected_actions": "[]", "original_expected_actions": "[]",
        "expected_answer": ans,
        "judge_metrics": "completeness|coherence|conciseness|output_latency_milliseconds",
        "source_definition": SRC_DEF, "requires_confirmation_before_tool": "true",
        "allowed_tools": "", "forbidden_tools": "HelpIqAgentEscalateAction|HelpIqAgentMultiplierSoftwareRequests",
        "tool_policy": "human_handoff_gated",
        "tool_policy_notes": "Bare intent with no issue: clarify first; no ticket and no button on turn 1.",
        "allowed_topics": "Escalation", "topic_policy": "expected_topic_only",
        "topic_policy_notes": "Use the expected topic from the canonical test row.",
        "notes": "HELPEXP-453 UGB: bare-intent regression guard (no button, no premature ticket).",
    })
    return base

new_single = [
    single_row(smax+1, "I want to talk to a human",
        "Sure — what's the IT issue you want the ticket for (for example: laptop, VPN, Okta/MFA, software access, hardware)?",
        "Bare Human Request"),
    single_row(smax+2, "create a ticket",
        "Happy to. What's the IT issue you want the ticket for (for example: laptop problem, VPN, Okta/MFA, software access, hardware request)?",
        "Bare Ticket Request"),
    single_row(smax+3, "escalate this",
        "Sure — what's the IT issue you'd like escalated (for example: laptop, network/VPN, Okta/MFA, software access)?",
        "Bare Escalate Request"),
]
added_single = [r for r in new_single if r["test_id"] not in existing_single_ids]
single_rows.extend(added_single)
write(SINGLE, single_rows, single_cols)
print(f"SINGLE: added {len(added_single)} rows -> total {len(single_rows)}")
print("\nDONE")
