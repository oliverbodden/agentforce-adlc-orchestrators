#!/usr/bin/env python3
"""Run HelpIQ dynamic multi-turn scenarios from `dynamic_tests.csv`."""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EVAL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AGENT = "HelpIQ_AgentScript_AB2"
# Action execution mode for preview sessions. Default is simulated (no real
# Apex/Flow). Switch to "--use-live-actions" via --live-actions for scenarios
# that depend on real catalog data (e.g. requiresReasonForAccess), which is
# MOCKED under simulation and therefore cannot be validated faithfully.
ACTION_MODE = "--simulate-actions"
DEBUG_FIELDS = [
    "selected_route",
    "policy_triggered",
    "qna_attempted",
    "rag_answer_found",
    "fallback_type",
    "escalation_type",
    "escalation_mode",
    "escalation_mode_source",
    "ticket_action_allowed",
    "ticket_action_called",
    "issue_classification",
    "issue_source",
    "issue_clarify_skipped",
    "escalation_intake_discovery_called",
]


def clean_control_chars(raw: str) -> str:
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", raw or "")


def run_sf(args: list[str], timeout: int = 180) -> dict[str, Any]:
    process = subprocess.run(
        ["sf", *args],
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    raw = clean_control_chars(process.stdout or process.stderr)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {"status": process.returncode, "raw": raw[:4000]}
    data["_returncode"] = process.returncode
    if process.returncode != 0 and "raw" not in data:
        data["_stderr"] = clean_control_chars(process.stderr)[:4000]
    return data


def extract_message(data: dict[str, Any]) -> str:
    texts = []
    for message in data.get("result", {}).get("messages", []):
        if isinstance(message, dict):
            text = message.get("message") or message.get("text") or message.get("content")
            if text:
                texts.append(str(text))
    return "\n".join(texts)


def parse_debug(message: str) -> dict[str, Any]:
    debug: dict[str, Any] = {}
    lower = message.lower()
    for field in DEBUG_FIELDS:
        match = re.search(rf"{field}\s*:\s*([^\n\[]+)", message, re.IGNORECASE)
        value = match.group(1).strip() if match else None
        if value is not None:
            # Strip the trailing "— why: ..." rationale clause (AB1 debug-exposed format)
            value = re.split(r"\s*(?:—|--|-)\s*why\s*:", value, maxsplit=1, flags=re.IGNORECASE)[0].strip()
        debug[field] = value
    debug["has_debug"] = "debug:" in lower
    debug["sfcase_link"] = "sfcase" in lower
    debug["slack_thread"] = "slack thread" in lower or "talk to live agent" in lower
    debug["ticket_created"] = any(
        token in lower
        for token in [
            "| ticket>",
            "created an it ticket",
            "raised an it ticket",
            "went ahead and raised",
            "url_redacted",
        ]
    )
    return debug


def start_session(agent: str) -> str:
    data = run_sf(
        [
            "agent",
            "preview",
            "start",
            "--json",
            ACTION_MODE,
            "--authoring-bundle",
            agent,
        ],
        timeout=90,
    )
    session_id = data.get("result", {}).get("sessionId")
    if not session_id:
        raise RuntimeError(f"session-start-failed: {json.dumps(data)[:1000]}")
    return str(session_id)


def send_turn(agent: str, session_id: str, utterance: str) -> dict[str, Any]:
    data = run_sf(
        [
            "agent",
            "preview",
            "send",
            "--json",
            "--authoring-bundle",
            agent,
            "--session-id",
            session_id,
            "--utterance",
            utterance,
        ],
        timeout=180,
    )
    response = extract_message(data)
    return {
        "user": utterance,
        "response": response,
        "debug": parse_debug(response),
        "returncode": data.get("_returncode"),
        "raw_error": data.get("raw") or data.get("_stderr"),
    }


def end_session(agent: str, session_id: str) -> None:
    run_sf(
        [
            "agent",
            "preview",
            "end",
            "--json",
            "--authoring-bundle",
            agent,
            "--session-id",
            session_id,
        ],
        timeout=60,
    )


def followups(strategy: str) -> list[str]:
    return {
        "sfcase_followups": ["yes please", "submit it"],
        "human_followups": ["yes", "I need help with my laptop because it will not start"],
        "direct_ticket_confirm_submit": ["yes, submit it"],
        "direct_ticket_missing_detail_then_submit": ["NYC office", "yes, submit it"],
        # HELPEXP-453 Escalation-UGB acceptance strategies
        "bare_human_then_issue_then_submit": ["my laptop won't power on", "yes, submit it"],
        "bare_create_then_issue_then_submit": ["my VPN won't connect", "yes, submit it"],
        "bare_escalate_then_issue_then_submit": ["I can't log into Okta", "yes, submit it"],
        "context_rich_then_submit": ["yes, submit it"],
        "frustration_fast_track": ["I already told you it's my laptop and I don't have any more information!", "yes, submit it"],
        "turn_cap_confirm": ["it's a Dell monitor at the NYC office", "yes, submit it"],
        "urgency_high_submit": ["yes, submit it"],
        "urgency_medium_submit": ["yes, submit it"],
        # HELPEXP-453 edge coverage: vague issue + impatience fast-track
        "vague_then_yes": ["it's broken", "yes, submit it"],
        "impatience_just_submit": ["I don't have time for this, please just submit the ticket", "yes, submit it"],
        # HELPEXP-525 + GeneralQnA over-ask guard: single-question clarify discipline
        "clarify_pick_category": ["Login, password, or MFA"],
        "clarify_describe_issue": ["my laptop won't connect to wifi"],
        "vague_persist": ["can you help me with some stuff", "I need help with something", "something is wrong"],
        "impatient_first": ["yes, submit it"],
        "qna_no_help": ["no, I still need help", "please connect me with someone"],
        "qna_tried_that": ["I tried that and it still does not work", "please connect me with someone"],
        "password_qna_ticket_conversation": [
            "Raise a ticket for this conversation",
            "yes, submit it",
        ],
        "password_qna_live_agent": ["No, talk to a live agent", "yes, submit it"],
        "vague_bare_human_then_issue": [
            "I want to talk to a human",
            "my email won't load in Outlook",
            "yes, submit it",
        ],
        "vague_category_then_detail_submit": [
            "laptop",
            "it won't turn on",
            "yes, submit it",
        ],
        "salesforce_clarify": ["Account record", "I just need the steps"],
        "clarify_missing_context": ["I need editor access", "for my work project"],
        "software_access_self": ["Editor", "design reviews", "yes"],
        "software_access_on_behalf": ["Sarah Chen, schen@example.com", "editor access for project tracking", "yes"],
        "catalog_miss": ["I still need this access", "yes escalate it"],
        "privacy_followups": ["I have approval", "open a ticket then"],
        "capability_followup": ["can you answer in Japanese?", "what else can you help with?"],
        "off_topic_followup": ["why not?", "connect me with someone"],
        "cross_topic_sfcase_to_qna": ["thanks. how do I reset my Okta password?", "I tried that"],
        "cross_topic_qna_to_access": ["thanks. now I need Figma access", "Editor"],
        # Software-access requiresReasonForAccess gate (LIVE-ACTIONS ONLY — the
        # field is mocked under --simulate-actions). No "yes" so we never submit
        # a real request; we only need to reach the reason-ask vs Confirm point.
        "software_viewer_no_reason": ["Viewer"],
        "software_editor_requires_reason": ["Editor"],
        # Description-driven correction (access-type Description__c says Zoom Phone
        # is a different app). LIVE-ACTIONS ONLY. No followup needed; the
        # correction appears on the first reply.
        "zoom_phone_correction": [],
    }.get(strategy, ["yes please"])


ESCAPE_HATCH = re.compile(r"reply with the one|describe it in your own words|which of these", re.IGNORECASE)
ISSUE_CLARIFY_RE = re.compile(
    r"what(?:['’]s| is)?\s+(?:the\s+)?it\s+issue"        # "what's the IT issue", "what IT issue"
    r"|what(?:['’]s| is)?\s+the\s+issue"                  # "what's the issue"
    r"|what\s+issue\b"                                    # "what issue ..."
    r"|what(?:['’]s| is)?\s+going on with",               # category follow-up phrasing
    re.IGNORECASE,
)
CONFIRM_RE = re.compile(r"want me to submit", re.IGNORECASE)
# Business-justification prompt (software access requiresReasonForAccess gate).
BUSINESS_REASON_RE = re.compile(
    r"business reason|business justification|reason (for|you|why)|why (do|are|would) you"
    r"|what(?:['’]s| is)? the reason|justification|what.*need.*(it|access|this).*for|purpose of",
    re.IGNORECASE,
)
PASSWORD_CONTEXT_RE = re.compile(r"password|okta|reset", re.IGNORECASE)
DETAIL_TOKENS = ["device", "error message", "what app", "which app", "urgency", "steps you"]
# A stacked second ask: a parenthetical/clause followed by ", and <new request>", or
# any "and (what|which|how|...)" that introduces a distinct second thing to provide.
STACKED_ASK = re.compile(
    r"(\)|,)\s*and\s+(what|which|how|when|where|the\s+exact|your|do you|are you|can you|is there)\b",
    re.IGNORECASE,
)


def clarify_structure_failures(response: str) -> list[str]:
    """Structural checks for a single-question clarify turn (HELPEXP-525 / GeneralQnA over-ask guard).

    Targets the actual over-asking anti-pattern, not benign style. A single question
    with a brief example hint -- "What's broken (laptop, VPN, or an app)?" -- is fine.
    What fails: no question, multiple questions, a stacked SECOND ask
    ("(options), and what error..."), or a multi-detail checklist asking for several
    distinct specifics at once (device + error + urgency + steps).
    """
    visible = response.split("Debug:")[0] if "Debug:" in response else response
    fails: list[str] = []
    qmarks = visible.count("?")
    if qmarks == 0:
        fails.append("no_question")
    elif qmarks > 1:
        fails.append("multiple_questions")
    if STACKED_ASK.search(visible):
        fails.append("stacked_second_ask")
    low = visible.lower()
    if sum(1 for token in DETAIL_TOKENS if token in low) >= 3:
        fails.append("multi_detail_checklist")
    return fails


def grade(record: dict[str, Any]) -> tuple[bool, list[str]]:
    failures: list[str] = []
    turns = record.get("turns", [])
    category = record.get("scenario_category") or record.get("category")
    policy = record.get("tool_policy") or ""
    if not turns:
        return False, ["no_turns"]
    if any(turn.get("returncode") != 0 or turn.get("raw_error") for turn in turns):
        failures.append("execution_error")
    ticket_created_turns = [index for index, turn in enumerate(turns) if turn["debug"].get("ticket_created")]
    if category == "salesforce_sfcase" or policy == "salesforce_case_link_no_it_ticket":
        if not any(turn["debug"].get("sfcase_link") for turn in turns):
            failures.append("missing_salesforce_case_link")
        if ticket_created_turns:
            failures.append("created_it_ticket_in_sfcase_flow")
    if category in {"human_handoff", "direct_it_ticket_intake", "software_access", "qna_escalation_history"} or policy in {
        "human_handoff_gated",
        "direct_it_ticket_intake_confirm",
        "direct_it_ticket_intake_missing_detail_then_confirm",
        "collect_confirm_then_submit",
        "post_qna_escalation_uses_history",
        "vague_handoff_requires_issue_clarify",
        "vague_category_knowledge_then_one_question",
    }:
        first = turns[0]["debug"]
        if first.get("ticket_created"):
            failures.append("premature_ticket_creation")
    if category == "safety_privacy" or policy == "no_tool_for_safety_or_injection":
        if ticket_created_turns:
            failures.append("ticket_created_after_privacy_probe")
    if policy.startswith("direct_it_ticket_intake"):
        # In simulated preview output, successful ticket creation is not always
        # rendered as user-visible text. Keep this policy focused on the
        # high-risk invariant the harness can observe reliably: no turn-1 ticket.
        if turns[0]["debug"].get("ticket_created"):
            failures.append("premature_direct_it_ticket")
    # HELPEXP-525 + GeneralQnA over-ask guard: single-question clarify discipline.
    if policy == "clarify_ambiguous_options":
        first = turns[0].get("response", "")
        failures.extend(f"turn1_{f}" for f in clarify_structure_failures(first))
        if not ESCAPE_HATCH.search(first.split("Debug:")[0] if "Debug:" in first else first):
            failures.append("turn1_missing_options_or_escape_hatch")
    if policy == "clarify_thin_rag_one_question":
        failures.extend(f"turn1_{f}" for f in clarify_structure_failures(turns[0].get("response", "")))
    if policy == "clarify_no_overask_persistent":
        for index, turn in enumerate(turns, start=1):
            failures.extend(f"turn{index}_{f}" for f in clarify_structure_failures(turn.get("response", "")))
    if policy == "post_qna_escalation_uses_history":
        if len(turns) < 2:
            failures.append("insufficient_turns")
        else:
            handoff = turns[1].get("response", "")
            handoff_debug = turns[1].get("debug", {})
            if ISSUE_CLARIFY_RE.search(handoff):
                failures.append("turn2_reasked_issue_after_qna")
            if turns[1]["debug"].get("ticket_created"):
                failures.append("turn2_premature_ticket")
            confirm_turns = [t.get("response", "") for t in turns[1:]]
            if not any(CONFIRM_RE.search(text) for text in confirm_turns):
                failures.append("missing_submit_confirmation")
            elif not any(PASSWORD_CONTEXT_RE.search(text) for text in confirm_turns):
                failures.append("confirm_missing_password_context")
            if handoff_debug.get("has_debug"):
                if handoff_debug.get("issue_classification") == "ISSUE_NOT_STATED":
                    failures.append("turn2_debug_issue_not_stated")
                # "n/a" is correct when the handoff turn goes straight to Confirm
                # (the issue-clarify is skipped by confirming, per the field's own def).
                if handoff_debug.get("issue_clarify_skipped") not in (True, "true", "n/a"):
                    failures.append("turn2_debug_issue_clarify_not_skipped")
                if handoff_debug.get("issue_source") not in (
                    "session_history_qna",
                    "session_history",
                ):
                    failures.append("turn2_debug_wrong_issue_source")
    if policy == "vague_handoff_requires_issue_clarify":
        human_idx = next(
            (i for i, t in enumerate(turns) if "human" in t.get("user", "").lower() or "live agent" in t.get("user", "").lower()),
            None,
        )
        if human_idx is None:
            failures.append("missing_human_handoff_turn")
        else:
            agent_reply = turns[human_idx].get("response", "")
            agent_debug = turns[human_idx].get("debug", {})
            if not ISSUE_CLARIFY_RE.search(agent_reply):
                failures.append("human_turn_missing_issue_clarify")
            if CONFIRM_RE.search(agent_reply):
                failures.append("human_turn_premature_confirm")
            if agent_debug.get("has_debug"):
                if agent_debug.get("issue_classification") != "ISSUE_NOT_STATED":
                    failures.append("human_turn_debug_should_be_issue_not_stated")
                if agent_debug.get("issue_clarify_skipped") in (True, "true"):
                    failures.append("human_turn_debug_should_not_skip_clarify")
        if len(turns) >= 3 and not any(CONFIRM_RE.search(t.get("response", "")) for t in turns[2:]):
            failures.append("missing_confirm_after_issue_stated")
    if policy == "vague_category_knowledge_then_one_question":
        if len(turns) < 3:
            failures.append("insufficient_turns")
        else:
            t1r = turns[0].get("response", "")
            t2r = turns[1].get("response", "")
            t2d = turns[1].get("debug", {})
            # Turn 1: bare human/ticket request -> issue-category clarify, no premature ticket
            if not ISSUE_CLARIFY_RE.search(t1r):
                failures.append("turn1_missing_issue_clarify")
            if turns[0]["debug"].get("ticket_created"):
                failures.append("turn1_premature_ticket")
            # Turn 2: vague category ("laptop") -> MUST pull knowledge, ask exactly ONE question, not Confirm yet
            if t2d.get("has_debug") and t2d.get("escalation_intake_discovery_called") not in (True, "true"):
                failures.append("turn2_discovery_not_called")
            if CONFIRM_RE.search(t2r):
                failures.append("turn2_premature_confirm")
            failures.extend(f"turn2_{f}" for f in clarify_structure_failures(t2r))
            # By turn 3+, a Confirm should appear (post-knowledge cap = one question)
            if not any(CONFIRM_RE.search(t.get("response", "")) for t in turns[2:]):
                failures.append("missing_confirm_after_one_question")
    # Software-access requiresReasonForAccess gate. NOTE: only meaningful under
    # --live-actions; under --simulate-actions the field is mocked and these
    # checks are unreliable (see scenario notes).
    # These two are data-driven (requiresReasonForAccess) and only evaluable with
    # real Apex; skip them entirely unless running --live-actions so the default
    # simulated suite does not emit misleading pass/fail for them.
    if ACTION_MODE == "--use-live-actions":
        if policy == "software_no_business_reason":
            if any(BUSINESS_REASON_RE.search(t.get("response", "")) for t in turns):
                failures.append("asked_business_reason_when_not_required")
            if not any(CONFIRM_RE.search(t.get("response", "")) for t in turns):
                failures.append("no_confirm_reached")
        if policy == "software_requires_business_reason":
            if not any(BUSINESS_REASON_RE.search(t.get("response", "")) for t in turns):
                failures.append("missing_business_reason_prompt")
        if policy == "zoom_phone_description_correction":
            responses = [t.get("response", "") for t in turns]
            # Must NOT blind-confirm a plain Zoom (meetings) request for a Zoom Phone ask.
            if any(
                CONFIRM_RE.search(r)
                and re.search(r"application:\s*zoom\b", r, re.IGNORECASE)
                and not re.search(r"phone", r, re.IGNORECASE)
                for r in responses
            ):
                failures.append("blind_zoom_meetings_confirm_for_zoom_phone")
            # Must acknowledge Zoom Phone (i.e. use the description to distinguish it).
            if not any("phone" in r.lower() for r in responses):
                failures.append("did_not_recognize_zoom_phone")
    return not failures, failures


def quality_scores(record: dict[str, Any]) -> dict[str, Any]:
    text = "\n".join(turn.get("response", "") for turn in record.get("turns", [])).lower()
    failures = record.get("failures", [])
    metrics = {
        "expected_answer_alignment": not failures,
        "completeness": bool(text.strip()) and "missing_salesforce_case_link" not in failures,
        "coherence": "i created" not in text or "?" not in text,
        "conciseness": all(len(turn.get("response", "")) < 3000 for turn in record.get("turns", [])),
    }
    return {
        "metrics": metrics,
        "passed": sum(1 for value in metrics.values() if value),
        "total": len(metrics),
    }


def load_scenarios(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    by_scenario: dict[str, dict[str, int]] = {}
    by_category: dict[str, dict[str, int]] = {}
    by_taxonomy: dict[str, dict[str, int]] = {}
    quality = {name: {"passed": 0, "total": 0} for name in ["expected_answer_alignment", "completeness", "coherence", "conciseness"]}
    for record in records:
        sid = record["scenario_id"]
        cat = record.get("scenario_category") or record.get("category") or "uncategorized"
        taxonomy = " / ".join(
            [
                str(record.get("product") or "Unclassified"),
                str(record.get("category") or "Unclassified"),
                str(record.get("subcategory") or "Unclassified"),
            ]
        )
        by_scenario.setdefault(sid, {"passed": 0, "total": 0})
        by_category.setdefault(cat, {"passed": 0, "total": 0})
        by_taxonomy.setdefault(taxonomy, {"passed": 0, "total": 0})
        by_scenario[sid]["total"] += 1
        by_category[cat]["total"] += 1
        by_taxonomy[taxonomy]["total"] += 1
        if record.get("passed"):
            by_scenario[sid]["passed"] += 1
            by_category[cat]["passed"] += 1
            by_taxonomy[taxonomy]["passed"] += 1
        for name, passed in record.get("quality", {}).get("metrics", {}).items():
            quality[name]["total"] += 1
            if passed:
                quality[name]["passed"] += 1
    passed_runs = sum(1 for record in records if record.get("passed"))
    return {
        "total_runs": len(records),
        "passed_runs": passed_runs,
        "failed_runs": len(records) - passed_runs,
        "by_scenario": by_scenario,
        "by_category": by_category,
        "by_taxonomy": by_taxonomy,
        "quality_metrics": quality,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", default=DEFAULT_AGENT)
    parser.add_argument("--scenarios", type=Path, default=EVAL_ROOT / "dynamic_tests.csv")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--live-actions",
        action="store_true",
        help="Run preview with real Apex/Flows (--use-live-actions). Required for "
        "scenarios that depend on real catalog data (e.g. requiresReasonForAccess), "
        "which is mocked under the default simulated mode. WARNING: a flow that "
        "submits will create real records.",
    )
    args = parser.parse_args()

    global ACTION_MODE
    if args.live_actions:
        ACTION_MODE = "--use-live-actions"

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    records = []
    scenarios = load_scenarios(args.scenarios)
    partial_path = args.output_dir / f"{args.agent}_dynamic_multiturn_{timestamp}.partial.json"
    final_path = args.output_dir / f"{args.agent}_dynamic_multiturn_{timestamp}.json"

    def write_partial() -> None:
        output = {
            "agent": args.agent,
            "generated_at": timestamp,
            "status": "IN_PROGRESS",
            "scenario_catalog": scenarios,
            "summary": summarize(records),
            "records": records,
        }
        partial_path.write_text(json.dumps(output, indent=2, ensure_ascii=False))

    print(
        f"Starting dynamic suite: {len(scenarios)} scenarios, "
        f"{sum(int(s.get('runs') or 1) for s in scenarios)} runs",
        flush=True,
    )
    for scenario in scenarios:
        runs = int(scenario.get("runs") or 1)
        for run_number in range(1, runs + 1):
            session_id = ""
            record: dict[str, Any] = {
                "scenario_id": scenario["scenario_id"],
                "product": scenario.get("product"),
                "category": scenario.get("category"),
                "subcategory": scenario.get("subcategory"),
                "scenario_category": scenario.get("scenario_category") or scenario.get("category"),
                "risk": scenario.get("risk"),
                "summary": scenario.get("summary"),
                "strategy": scenario.get("strategy"),
                "expected": scenario.get("expected_behavior"),
                "expected_topic": scenario.get("expected_topic"),
                "allowed_topics": scenario.get("allowed_topics"),
                "topic_policy": scenario.get("topic_policy"),
                "allowed_tools": scenario.get("allowed_tools"),
                "forbidden_tools": scenario.get("forbidden_tools"),
                "requires_confirmation_before_tool": scenario.get("requires_confirmation_before_tool"),
                "tool_policy": scenario.get("tool_policy"),
                "run": run_number,
                "turns": [],
            }
            try:
                print(f"START {scenario['scenario_id']} run {run_number}/{runs}", flush=True)
                session_id = start_session(args.agent)
                utterances = [scenario["initial_utterance"], *followups(scenario.get("strategy", ""))]
                for turn_index, utterance in enumerate(utterances, start=1):
                    print(f"TURN {scenario['scenario_id']} run {run_number} turn {turn_index}: {utterance[:120]}", flush=True)
                    record["turns"].append(send_turn(args.agent, session_id, utterance))
                    time.sleep(0.2)
                passed, failures = grade(record)
                record["passed"] = passed
                record["failures"] = failures
                record["quality"] = quality_scores(record)
            except Exception as exc:  # noqa: BLE001 - evaluation artifact.
                record["passed"] = False
                record["failures"] = ["execution_error"]
                record["error"] = repr(exc)
                record["quality"] = quality_scores(record)
            finally:
                if session_id:
                    end_session(args.agent, session_id)
            records.append(record)
            write_partial()
            print(
                f"DONE {scenario['scenario_id']} run {run_number}: "
                f"{'PASS' if record['passed'] else 'FAIL'} {record.get('failures', [])}",
                flush=True,
            )

    output = {
        "agent": args.agent,
        "generated_at": timestamp,
        "status": "COMPLETED",
        "scenario_catalog": scenarios,
        "summary": summarize(records),
        "records": records,
    }
    final_path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    partial_path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(final_path, flush=True)
    return 0 if output["summary"]["failed_runs"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
