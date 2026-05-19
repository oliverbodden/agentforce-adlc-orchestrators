#!/usr/bin/env python3
"""Iter 5 trace inspection v2 — extract FunctionStep inputs/outputs.

Emits a markdown report with, for each scenario turn:
  * which actions ran
  * their input args
  * their output (truncated)
  * the planner reply

Then we can hand-compare the action outputs to the Debug `Retrieval` field
the model put in the planner reply.
"""
import json
import re
from pathlib import Path

TICKET = Path(
    "/Users/obguzman/agentforce-project/adlc/agents/HelpIQ_AgentScript__aicommon/tickets/HELPEXP-286-multiplier-ugb-port"
)
TRACES_ROOT = Path(
    "/Users/obguzman/agentforce-project/.sfdx/agents/HelpIQ_AgentScript/sessions"
)


def latest_iter():
    cands = sorted(TICKET.glob("results/iter3-scenarios-*.json"))
    return cands[-1]


def trunc(val, n=1500):
    s = val if isinstance(val, str) else json.dumps(val, indent=2)
    if len(s) > n:
        s = s[:n] + f"\n…<{len(s) - n} chars truncated>"
    return s


def fence(s, lang="json"):
    return f"```{lang}\n{s}\n```"


def extract_retrieval_field(planner_text):
    if not planner_text:
        return None
    m = re.search(r"Retrieval[\s\S]*?(?=\n\s*(Strategy|Plan|RawSlots|Pivot|Submit|$))", planner_text)
    return m.group(0) if m else None


def walk_session(session_id):
    traces_dir = TRACES_ROOT / session_id / "traces"
    if not traces_dir.exists():
        return []
    return sorted(traces_dir.glob("*.json"), key=lambda p: p.stat().st_mtime)


def parse_trace(path):
    with open(path) as f:
        t = json.load(f)
    plan = t.get("plan", [])
    user_msg = None
    planner = None
    functions = []
    for step in plan:
        typ = step.get("type")
        if typ == "UserInputStep":
            user_msg = step.get("message")
        elif typ == "PlannerResponseStep":
            planner = step.get("message")
        elif typ == "FunctionStep":
            fn = step.get("function", {})
            functions.append({
                "name": fn.get("name"),
                "input": fn.get("input"),
                "output": fn.get("output"),
                "latency_ms": step.get("executionLatency"),
            })
    return {
        "intent": t.get("intent"),
        "user_msg": user_msg,
        "planner": planner,
        "functions": functions,
    }


def main():
    iter_path = latest_iter()
    with open(iter_path) as f:
        iter_data = json.load(f)

    out_lines = [f"# Iter 5 trace inspection v2 — `{iter_path.name}`\n"]
    out_lines.append(
        "Validates: (a) what `HelpIqAgentApplicationAccessDetails` actually returned vs.\n"
        "the model's self-reported Debug `Retrieval`; (b) whether `HelpIqAgentMultiplierSoftwareRequests`\n"
        "actually ran on Submit-eligible turns; (c) whether tickets are real (URLs).\n"
    )

    findings = []

    for scenario in iter_data["scenarios"]:
        sid = scenario["id"]
        sess = scenario["session_id"]
        traces = walk_session(sess)
        out_lines.append(f"\n---\n\n## {sid}\nsession `{sess}` · trace_count={len(traces)}\n")

        for tidx, tp in enumerate(traces):
            data = parse_trace(tp)
            out_lines.append(f"\n### T{tidx + 1} · trace `{tp.stem}`\n")
            out_lines.append(f"- intent: `{data['intent']}`\n")
            out_lines.append(f"- user_msg: {trunc(data['user_msg'], 220)}\n")
            retrieval_field = extract_retrieval_field(data["planner"])

            if not data["functions"]:
                out_lines.append("- **no function calls** (model produced reply without invoking any action)\n")
            for fi, fn in enumerate(data["functions"]):
                out_lines.append(f"\n**fn{fi + 1}** `{fn['name']}` ({fn['latency_ms']}ms)\n")
                out_lines.append(f"\ninput:\n{fence(trunc(fn['input'], 800))}\n")
                out_lines.append(f"\noutput:\n{fence(trunc(fn['output'], 4000))}\n")

            if retrieval_field:
                out_lines.append(f"\n**Debug.Retrieval (model self-report)**\n{fence(trunc(retrieval_field, 1200), 'text')}\n")

            findings.append({
                "scenario": sid,
                "turn": tidx + 1,
                "user_msg": data["user_msg"],
                "intent": data["intent"],
                "functions": [{"name": f["name"], "input_keys": list((f.get("input") or {}).keys()), "output_keys": list((f.get("output") or {}).keys()) if isinstance(f.get("output"), dict) else None, "latency_ms": f["latency_ms"]} for f in data["functions"]],
                "retrieval_field_present": bool(retrieval_field),
            })

    out_path = TICKET / "results" / "iter5-trace-inspection-v2.md"
    out_path.write_text("".join(out_lines))
    print(f"wrote {out_path} ({out_path.stat().st_size} bytes)")

    findings_path = TICKET / "results" / "iter5-trace-inspection-v2-findings.json"
    findings_path.write_text(json.dumps(findings, indent=2))
    print(f"wrote {findings_path}")


if __name__ == "__main__":
    main()
