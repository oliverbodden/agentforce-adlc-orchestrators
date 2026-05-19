#!/usr/bin/env python3
"""Trace inspection for iter 5 multiplier sessions.

Walks every trace in every iter-5 session and emits a compact per-turn summary:
  * which actions were invoked
  * the raw retrieval/result payload from HelpIqAgentApplicationAccessDetails
  * the raw payload from HelpIqAgentMultiplierSoftwareRequests (Submit)
  * the Planner response text

Then we can hand-compare against the model's Debug `Retrieval` field for
hallucination/UUID checks.
"""
import json
import os
import sys
from pathlib import Path

TICKET = Path(
    "/Users/obguzman/agentforce-project/adlc/agents/HelpIQ_AgentScript__aicommon/tickets/HELPEXP-286-multiplier-ugb-port"
)
TRACES_ROOT = Path("/Users/obguzman/agentforce-project/.sfdx/agents/HelpIQ_AgentScript/sessions")


def latest_iter_results():
    cands = sorted(TICKET.glob("results/iter3-scenarios-*.json"))
    if not cands:
        sys.exit("no iter scenario results found")
    return cands[-1]


def short(val, n=400):
    s = json.dumps(val, indent=2) if not isinstance(val, str) else val
    if len(s) > n:
        return s[:n] + f"... <{len(s) - n} more chars>"
    return s


def list_traces_for_session(session_id):
    traces_dir = TRACES_ROOT / session_id / "traces"
    if not traces_dir.exists():
        return []
    files = sorted(traces_dir.glob("*.json"), key=lambda p: p.stat().st_mtime)
    return files


def summarize_trace(path):
    with open(path) as f:
        t = json.load(f)
    plan = t.get("plan", [])
    user_msg = None
    actions = []
    planner_text = None
    for step in plan:
        typ = step.get("type")
        if typ == "UserInputStep":
            user_msg = step.get("message")
        elif typ == "PlannerResponseStep":
            planner_text = step.get("message")
        elif typ in {"ActionStep", "InvokeActionStep", "FunctionStep"}:
            actions.append(step)
        elif typ == "LLMStep":
            # Some Agent Script traces embed tool calls inside LLMStep
            for sub_key in ("toolCalls", "actions", "calls"):
                if sub_key in step:
                    for c in step[sub_key]:
                        actions.append({"type": typ + "." + sub_key, **c})
    return {
        "trace_path": str(path),
        "trace_id": path.stem,
        "intent": t.get("intent"),
        "topic": t.get("topic"),
        "user_msg": user_msg,
        "n_steps": len(plan),
        "step_types": [s.get("type") for s in plan],
        "actions": actions,
        "planner_text": planner_text,
    }


def find_action_outputs(trace_path):
    """Walk the trace looking for any node containing 'HelpIqAgent...' result data."""
    with open(trace_path) as f:
        t = json.load(f)
    hits = []
    interesting = (
        "HelpIqAgentApplicationAccessDetails",
        "HelpIqAgentMultiplierSoftwareRequests",
        "HelpIQ_QnA",
        "stage_request",
        "accept_confirmation",
    )

    def walk(node, path=""):
        if isinstance(node, dict):
            for k, v in node.items():
                kpath = f"{path}.{k}" if path else k
                if isinstance(v, str) and any(name in v for name in interesting):
                    # capture surrounding dict
                    hits.append({"path": kpath, "value_snippet": v[:300], "container_keys": list(node.keys())})
                walk(v, kpath)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")

    walk(t)
    return hits


def main():
    iter_path = latest_iter_results()
    with open(iter_path) as f:
        iter_data = json.load(f)

    out_path = TICKET / "results" / "iter5-trace-inspection.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    lines.append(f"# Iter 5 trace inspection — {iter_path.name}\n")
    lines.append(
        "Source-of-truth raw retrieval/action payloads pulled from .sfdx local traces.\n"
        "Use this to validate whether the model's Debug `Retrieval` field accurately "
        "reflects what `HelpIqAgentApplicationAccessDetails` actually returned, and "
        "whether `HelpIqAgentMultiplierSoftwareRequests` actually ran (and what payload).\n"
    )

    summary_actions = []

    for s in iter_data["scenarios"]:
        sid = s["id"]
        session_id = s["session_id"]
        lines.append(f"\n---\n\n## {sid}\nsession `{session_id}`\n")
        traces = list_traces_for_session(session_id)
        lines.append(f"trace count: {len(traces)}\n")
        if not traces:
            lines.append("_no traces on disk_\n")
            continue
        for tp in traces:
            summ = summarize_trace(tp)
            hits = find_action_outputs(tp)
            n_actions = len(summ["actions"])
            lines.append(f"\n### trace `{summ['trace_id']}`\n")
            lines.append(f"- intent: {summ['intent']}\n")
            lines.append(f"- user_msg: {short(summ['user_msg'], 200)}\n")
            lines.append(f"- step types: {summ['step_types']}\n")
            lines.append(f"- direct action steps captured: {n_actions}\n")
            lines.append(f"- planner reply: {short(summ['planner_text'], 350)}\n")
            if hits:
                lines.append(f"- string-hits referencing helper/action names: {len(hits)} (showing first 6)\n")
                for h in hits[:6]:
                    lines.append(f"  - `{h['path']}` → `{h['value_snippet']}`\n")
            summary_actions.append({
                "scenario": sid,
                "trace": summ["trace_id"],
                "intent": summ["intent"],
                "user_msg": summ["user_msg"],
                "n_steps": summ["n_steps"],
                "step_types": summ["step_types"],
                "n_actions": n_actions,
                "planner_snippet": (summ["planner_text"] or "")[:200],
            })

    out_path.write_text("".join(lines))
    print(f"wrote {out_path} ({out_path.stat().st_size} bytes)")

    json_path = TICKET / "results" / "iter5-trace-inspection-summary.json"
    json_path.write_text(json.dumps(summary_actions, indent=2))
    print(f"wrote {json_path}")


if __name__ == "__main__":
    main()
