#!/usr/bin/env python3
"""Generate AiEvaluationDefinition XML for the v9 multiplier regression test.

Reads the v7-proxy multiplier baseline (78 rows = 26 unique utterances × 3 trials)
and emits an AiEvaluationDefinition pinned to subjectVersion v9.

Metrics included per case:
  * topic_sequence_match  (expected: HelpIqAgentMultiplierSoftwareRequests)
  * completeness          (OOTB rubric, no expected value)
  * coherence             (OOTB rubric)
  * conciseness           (OOTB rubric)
  * output_latency_milliseconds (passive measure)

Metrics deliberately NOT included:
  * action_sequence_match — v9 introduces new helper actions (stage_request,
    accept_confirmation) that change the action trace shape vs. v7. A v7-derived
    expected_value would mark every v9 Submit case FAIL even when behavior is
    correct. Action-trace validation belongs in scripted scenario tests
    (iter3_run_scenarios.py + trace_inspect2.py), not in the regression battery.
  * bot_response_rating — requires reference responses from v7. We don't have
    them in the CSV (only first 120 chars). Skipping keeps this spec
    self-contained; add later by parsing source JSON if needed.
"""
import csv
import re
from pathlib import Path
from xml.sax.saxutils import escape

TICKET = Path(
    "/Users/obguzman/agentforce-project/adlc/agents/HelpIQ_AgentScript__aicommon/tickets/HELPEXP-286-multiplier-ugb-port"
)
BASELINE_CSV = TICKET / "results" / "baseline-v7proxy-multiplier-from-v4.csv"
OUT = Path(
    "/Users/obguzman/agentforce-project/force-app/main/default/aiEvaluationDefinitions/HelpIQ_v9_multiplier_baseline_78_5_16_1.aiEvaluationDefinition-meta.xml"
)
EVAL_NAME = "HelpIQ - v9 multiplier baseline - 78 - 5.16.1"
SUBJECT_NAME = "HelpIQ_AgentScript"
SUBJECT_VERSION = "v9"
TRIALS_PER_UTTERANCE = 3
EXPECTED_TOPIC = "HelpIqAgentMultiplierSoftwareRequests"


def load_unique_utterances(csv_path):
    """Return unique utterances preserving first-seen order."""
    seen = []
    seen_set = set()
    with open(csv_path) as f:
        for row in csv.DictReader(f):
            u = row["utterance"]
            if u not in seen_set:
                seen.append(u)
                seen_set.add(u)
    return seen


def build_testcase(utterance, trial_number):
    u = escape(utterance)
    return f"""    <testCase>
        <expectation>
            <expectedValue>{EXPECTED_TOPIC}</expectedValue>
            <name>topic_sequence_match</name>
        </expectation>
        <expectation>
            <name>completeness</name>
        </expectation>
        <expectation>
            <name>coherence</name>
        </expectation>
        <expectation>
            <name>conciseness</name>
        </expectation>
        <expectation>
            <name>output_latency_milliseconds</name>
        </expectation>
        <inputs>
            <utterance>{u}</utterance>
        </inputs>
        <number>{trial_number}</number>
    </testCase>"""


def main():
    utterances = load_unique_utterances(BASELINE_CSV)
    assert len(utterances) == 26, f"expected 26 unique utterances, got {len(utterances)}"

    cases = []
    for utt in utterances:
        for trial in range(1, TRIALS_PER_UTTERANCE + 1):
            cases.append(build_testcase(utt, trial))

    assert len(cases) == 78, f"expected 78 testCases, got {len(cases)}"

    body = "\n".join(cases)

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<AiEvaluationDefinition xmlns="http://soap.sforce.com/2006/04/metadata">
    <name>{EVAL_NAME}</name>
    <subjectName>{SUBJECT_NAME}</subjectName>
    <subjectType>AGENT</subjectType>
    <subjectVersion>{SUBJECT_VERSION}</subjectVersion>
{body}
</AiEvaluationDefinition>
"""

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(xml)
    print(f"wrote {OUT}")
    print(f"  unique utterances: {len(utterances)}")
    print(f"  total testCases:   {len(cases)} ({len(utterances)} × {TRIALS_PER_UTTERANCE})")
    print(f"  subjectVersion:    {SUBJECT_VERSION}")
    print(f"  expected_topic:    {EXPECTED_TOPIC} (uniform across all cases)")


if __name__ == "__main__":
    main()
