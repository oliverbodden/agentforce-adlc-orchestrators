#!/usr/bin/env python3
"""
HELPEXP-286 — Merge iter-5 multiplier subagent into v8 working draft.

Strategy
--------
Take v8 (org draft) as the base. Apply two surgical edits:
  1. Insert the 4 new iter-5 variables (pending_application_key, pending_access_type_key,
     pending_reason, confirmation_accepted) into the variables block,
     immediately after the existing v8 variables. Preserve qna_invoked and multiplierTicket.
  2. Replace the entire `subagent HelpIqAgentMultiplierSoftwareRequests:` block
     with the iter-5 local version. While replacing, splice into the new
     reasoning.actions wiring:
       - `set @variables.qna_invoked = True` on HelpIQ_QnA (preserves v8 escalation gate)
       - `set @variables.multiplierTicket = @outputs.ticketURL` on the Submit action
         (preserves v8 completion-tracking variable, even though new prompt
         does not read it — leaves it available for other consumers)

Everything else in v8 is preserved byte-for-byte: system, model_config, config,
language, start_agent agent_router (with descriptions and qna_invoked gate),
subagent GeneralQnA_HelpIQ (with qna_invoked sets/gates), Off_Topic,
Ambiguous_Question, Escalation.
"""
import sys
from pathlib import Path

REPO = Path("/Users/obguzman/agentforce-project")
V8 = REPO / "adlc/agents/HelpIQ_AgentScript__aicommon/tickets/HELPEXP-286-multiplier-ugb-port/originals/v8-current-pre-iter5.agent"
LOCAL = REPO / "force-app/main/default/aiAuthoringBundles/HelpIQ_AgentScript/HelpIQ_AgentScript.agent"
OUT = REPO / "force-app/main/default/aiAuthoringBundles/HelpIQ_AgentScript/HelpIQ_AgentScript.agent"


def read_lines(p: Path) -> list[str]:
    return p.read_text().splitlines(keepends=True)


def find_line(lines: list[str], needle: str, start: int = 0) -> int:
    for i in range(start, len(lines)):
        if lines[i].startswith(needle):
            return i
    raise ValueError(f"not found: {needle!r}")


def extract_block(lines: list[str], header_prefix: str, next_top_level_prefixes: tuple[str, ...]) -> tuple[int, int]:
    """Return (start_index_inclusive, end_index_exclusive) for a top-level block."""
    start = find_line(lines, header_prefix)
    end = len(lines)
    for i in range(start + 1, len(lines)):
        for p in next_top_level_prefixes:
            if lines[i].startswith(p):
                end = i
                return start, end
    return start, end


def main() -> None:
    v8 = read_lines(V8)
    local = read_lines(LOCAL)

    # --- (1) Build new variables block ---
    # v8 variables block runs from `variables:` to `start_agent`
    v8_var_start = find_line(v8, "variables:")
    v8_var_end = find_line(v8, "start_agent ", v8_var_start)

    # 4 iter-5 variables block (from local file)
    new_vars = [
        '    pending_application_key: mutable string = ""\n',
        '        description: "Multiplier ticket HELPEXP-286: applicationKey for a request the model has staged for user confirmation. Cleared after Submit succeeds."\n',
        '    pending_access_type_key: mutable string = ""\n',
        '        description: "Multiplier ticket HELPEXP-286: accessTypeKey for a request the model has staged for user confirmation. Cleared after Submit succeeds."\n',
        '    pending_reason: mutable string = ""\n',
        '        description: "Multiplier ticket HELPEXP-286: reasonForAccess for a request the model has staged for user confirmation. Cleared after Submit succeeds."\n',
        '    confirmation_accepted: mutable boolean = False\n',
        '        description: "Multiplier ticket HELPEXP-286: True only after the user has explicitly accepted the slot summary on the immediately-prior agent Confirm turn. Flipped back to False after Submit succeeds. Gates visibility of HelpIqAgentMultiplierSoftwareRequests action."\n',
    ]

    # Find last variable definition line in v8 (last non-blank, indented line before start_agent)
    # Strategy: insert immediately before the blank line that precedes start_agent.
    # v8 variables block:
    # 56  variables:
    # 57-58  glean_agent_id / description
    # 59-60  prompt_template_retriever_id / description
    # 61-62  qna_invoked / description
    # 63-64  multiplierTicket / description
    # 65  (blank)
    # 66  start_agent agent_router:
    insert_at = v8_var_end  # start_agent line
    # Walk backwards to skip the blank line(s) before start_agent
    while insert_at > v8_var_start and v8[insert_at - 1].strip() == "":
        insert_at -= 1
    # Now insert_at points just AFTER the last real variable definition line.

    new_variables_block = v8[:insert_at] + new_vars + v8[insert_at:]

    # --- (2) Replace multiplier subagent block ---
    # In the new (variables-extended) document, find subagent HelpIqAgentMultiplierSoftwareRequests:
    merged = new_variables_block
    mult_start = find_line(merged, "subagent HelpIqAgentMultiplierSoftwareRequests:")
    # Next top-level is `subagent Off_Topic:` per v8 ordering
    mult_end = find_line(merged, "subagent Off_Topic:", mult_start)

    # Extract iter-5 multiplier subagent block from local file
    local_mult_start = find_line(local, "subagent HelpIqAgentMultiplierSoftwareRequests:")
    local_mult_end = find_line(local, "subagent Off_Topic:", local_mult_start)
    new_mult_block = local[local_mult_start:local_mult_end]

    # --- (2a) Splice qna_invoked and multiplierTicket bookkeeping into reasoning.actions ---
    # Find the HelpIQ_QnA action wiring inside the multiplier subagent reasoning.actions block
    # and add `set @variables.qna_invoked = True` after the `with citationMode = ...` line.
    spliced: list[str] = []
    i = 0
    while i < len(new_mult_block):
        line = new_mult_block[i]
        spliced.append(line)
        # After `with citationMode = ...` on HelpIQ_QnA inside reasoning.actions, add qna_invoked set
        if (
            line.strip() == "with citationMode = ..."
            and i + 1 < len(new_mult_block)
            and "HelpIqAgentApplicationAccessDetails" in new_mult_block[i + 1]
        ):
            # Indentation: match `with` indentation (16 spaces in this file)
            indent = line[: len(line) - len(line.lstrip())]
            spliced.append(f"{indent}set @variables.qna_invoked = True\n")
        i += 1
    new_mult_block = spliced

    # Now splice `set @variables.multiplierTicket = @outputs.ticketURL` into the Submit action wiring.
    # Insert after `set @variables.pending_reason = ""` line.
    final_mult: list[str] = []
    for j, line in enumerate(new_mult_block):
        final_mult.append(line)
        if line.strip() == 'set @variables.pending_reason = ""':
            indent = line[: len(line) - len(line.lstrip())]
            final_mult.append(f"{indent}set @variables.multiplierTicket = @outputs.ticketURL\n")
    new_mult_block = final_mult

    # Stitch: v8 (variables-extended) up to mult_start + new_mult_block + v8 from mult_end
    final = merged[:mult_start] + new_mult_block + merged[mult_end:]

    OUT.write_text("".join(final))

    # Summary
    print(f"v8 base lines:        {len(v8)}")
    print(f"local source lines:   {len(local)}")
    print(f"merged output lines:  {len(final)}")
    print(f"vars inserted at v8 line: {insert_at + 1}")
    print(f"multiplier block: {mult_start + 1}..{mult_end} (replaced)")
    print(f"new multiplier block lines: {len(new_mult_block)}")
    print(f"output: {OUT}")


if __name__ == "__main__":
    main()
