# HelpIQ Evaluation

Ticket-agnostic evaluation package for the HelpIQ agent family.

This folder is the source of truth for test cases and reusable evaluation scripts. It should change only when the evaluation suite changes. Run outputs, raw results, debug traces, and ticket-specific reports belong outside this folder under `adlc/agents/HelpIQ/eval-runs/`.

## Files

- `single_turn_tests.csv` - master single-turn suite. Current coverage: `999` Testing Center cases. Includes corrected runtime `expected_actions`, `original_expected_actions`, allowed/forbidden tool policy, and confirmation-gating fields.
- `multi_turn_tests.csv` - master fixed multi-turn suite. Current coverage: `99` Testing Center cases with `conversation_history_json` for previous turns. Includes corrected runtime `expected_actions`, `original_expected_actions`, allowed/forbidden tool policy, and confirmation-gating fields.
- `dynamic_tests.csv` - master dynamic multi-turn scenario suite. Current coverage: `21` scenarios and `69` normalized dynamic runs. Includes tool-policy fields for Salesforce sfcase, software access, human handoff, direct IT ticket intake discovery, safety/privacy, and QnA follow-up behavior.
- `scripts/build_test_definitions.py` - rebuilds Salesforce `AiEvaluationDefinition` XML from the static CSV masters.
- `scripts/run_dynamic_tests.py` - runs dynamic preview scenarios from `dynamic_tests.csv`.
- `scripts/build_report.py` - builds one report from external single-turn, fixed multi-turn, and dynamic run result JSON files.

## Run Output Convention

Use a ticket or descriptive run folder, for example:

```bash
adlc/agents/HelpIQ/eval-runs/HELPEXP-274-ab2-repair/
adlc/agents/HelpIQ/eval-runs/2026-05-24-ab2-regression/
```

Do not put run artifacts under `evals/HelpIQ`.

## Rebuild Testing Center Definitions

```bash
python3 adlc/agents/HelpIQ/evals/HelpIQ/scripts/build_test_definitions.py \
  --subject-name HelpIQ_AgentScript_AB2 \
  --subject-version v1 \
  --output-dir adlc/agents/HelpIQ/eval-runs/HELPEXP-274-ab2-repair/generated-definitions
```

## Run Dynamic Scenarios

```bash
python3 adlc/agents/HelpIQ/evals/HelpIQ/scripts/run_dynamic_tests.py \
  --agent HelpIQ_AgentScript_AB2 \
  --output-dir adlc/agents/HelpIQ/eval-runs/HELPEXP-274-ab2-repair/dynamic
```

## Build Unified Report

Unified reports must use the iterative report template style: guide panel, agent/version cards, metric cards with bars, recommendation panel, and styled breakdown tables. Do not generate one-off lightweight HTML for release/regression review.

Use clean, policy-corrected result artifacts for progress reporting. Raw Salesforce result files are audit inputs only because their `topic_assertion` and `actions_assertion` may still reflect stale topic/action labels from older XML definitions.

Report generation must distinguish the **baseline** from the **evaluated agent** and enforce both roles explicitly for multi-agent reports:

- **Baseline** is the comparison anchor used for bar ordering and percentage-point deltas. For HELPEXP-274 AB repair reporting, the baseline is `HelpIQ20`.
- **Evaluated agent** is the candidate under review. The large headline percentages and recommendation framing should focus on this agent. For the current AB2 intake-confirmation evaluation, the evaluated agent is `HelpIQ_AgentScript_AB2`.
- Additional agents, such as `HelpIQ_AgentScript_AB1`, may be included as comparison/reference rows, but they should not silently become the baseline or the evaluated candidate.
- When another skill or agent builds a report, it must determine both roles explicitly before running `build_report.py`. If the user has not specified them, ask before generating the report.

Reports include a fixed **Score Mode** toggle under the **Report Guide** control so readers can change scoring from anywhere in the page. Selecting a mode updates the Results Summary, Recommendation, Sub-Agent benchmark, and Taxonomy benchmark sections where dynamic mapping data applies:

- **Tier-Balanced** - the preferred release-risk readout. It weights single-turn static benchmark, fixed multi-turn static benchmark, and dynamic behavior equally.
- **Volume-Weighted** - every static benchmark metric check and every dynamic behavior run count equally. This is useful for broad coverage but can let the 999-case single-turn suite dominate.

Do not hide score weighting inside a single unexplained number. Keep the score-mode formulas available in a hover info tip, and make applicable displayed metrics respond to the selected mode. **Benchmark Breakdown** includes four areas: Deterministic, Response Quality, Expected-Answer Alignment (static Testing Center), and Dynamic (behavior plus quality-proxy metrics). Latency remains static-only and should compare all agent versions.

The **Benchmark Breakdown** Dynamic panel uses `agent["dynamic"]["behavior"]` for behavior pass rate and `agent["dynamic"]["quality_metrics"]` for expected-answer alignment, completeness, coherence, and conciseness proxies. Cards follow the same all-agent comparison pattern as static breakdowns, with percentage-point deltas vs baseline and the evaluated agent as headline.

The **Benchmark by Sub-Agent** section is a pivot table:

- **Rows** — each agent version in the report (baseline, evaluated, and any reference agents).
- **Columns** — each expected sub-agent slice (`GeneralQnA_HelpIQ`, `Escalation`, `HelpIqAgentMultiplierSoftwareRequests`, `Prompt_Injection`, etc.).
- **Cell value** — the selected score-mode benchmark for that agent + sub-agent slice. Tier-balanced averages static and dynamic pass rates; volume-weighted sums passed/total across static and dynamic rows in the slice.
- **Delta line** — percentage-point change vs the baseline agent for the same sub-agent column (`0.0pp` on the baseline row when data exists, otherwise `-`).

The **Setup** section is coverage and context only. It lists per-agent test counts (single-turn, fixed multi-turn, dynamic runs), taxonomy dimensions, expected-topic counts, and tool-policy counts, plus baseline/evaluated/reference roles. It does **not** include pass rates, percentages, or other score results — those belong in Results, Recommendation, and breakdown sections.

Generate clean static results first:

```bash
python3 adlc/agents/HelpIQ/evals/HelpIQ/scripts/clean_results.py \
  --raw-results path/to/raw-single-results.json \
  --master-csv adlc/agents/HelpIQ/evals/HelpIQ/single_turn_tests.csv \
  --output path/to/clean-single-results.json

python3 adlc/agents/HelpIQ/evals/HelpIQ/scripts/clean_results.py \
  --raw-results path/to/raw-fixed-multi-results.json \
  --master-csv adlc/agents/HelpIQ/evals/HelpIQ/multi_turn_tests.csv \
  --output path/to/clean-fixed-multi-results.json
```

```bash
python3 adlc/agents/HelpIQ/evals/HelpIQ/scripts/build_report.py \
  --single-results path/to/clean-single-results.json \
  --multi-results path/to/clean-fixed-multi-results.json \
  --dynamic-results path/to/dynamic-results.json \
  --output-dir adlc/agents/HelpIQ/eval-runs/HELPEXP-274-ab2-repair/report
```

For multi-agent comparison reports, set both roles explicitly. Example:

```bash
python3 adlc/agents/HelpIQ/evals/HelpIQ/scripts/build_report.py \
  --baseline-agent-label HelpIQ20 \
  --primary-agent-label HelpIQ_AgentScript_AB2 \
  --agent-run "HelpIQ20::path/to/helpiq20-single-clean.json::path/to/helpiq20-multi-clean.json::path/to/helpiq20-dynamic-summary.json" \
  --agent-run "HelpIQ_AgentScript_AB2::path/to/ab2-single-clean.json::path/to/ab2-multi-clean.json::path/to/ab2-dynamic-results.json" \
  --agent-run "HelpIQ_AgentScript_AB1::path/to/ab1-single-clean.json::path/to/ab1-multi-clean.json::path/to/ab1-dynamic-summary.json" \
  --output-dir adlc/agents/HelpIQ/eval-runs/HELPEXP-274-ab2-repair/report
```

## Tool Policy Columns

The static CSVs distinguish old test labels from runtime tool assertions:

- `original_expected_actions` preserves the old Testing Center action expectation for audit/review.
- `expected_actions` is the corrected runtime tool assertion used when rebuilding XML.
- `allowed_tools` lists tools that may be invoked on the row.
- `forbidden_tools` lists tools that must not be invoked on the row.
- `requires_confirmation_before_tool` marks rows where submit/escalation tools are only valid after explicit confirmation or continued handoff.
- `tool_policy` and `tool_policy_notes` explain the decision, for example `salesforce_case_link_no_it_ticket`, `stage_before_confirmation`, `submit_only_after_confirmation`, `lookup_access_details_only`, `qna_allowed_no_ticket`, or `no_tool_for_safety_or_injection`.

Key decisions encoded in the masters:

- Salesforce sfcase fallback may use QnA/retrieval but must not create an IT ticket.
- Safety, privacy, and prompt-injection turns must not invoke tools.
- Software access flows may look up access details while gathering information, but submit/escalation tools require confirmation.
- Human handoff is gated: offer/clarify first, then create a handoff ticket only after context and confirmation/continued request.
- Pseudo-control actions such as `go_to_GeneralQnA_HelpIQ`, `stage_request`, `stage_escalation`, `accept_confirmation`, and `accept_escalation_confirmation` are preserved only in `original_expected_actions`; they are not runtime tool assertions.

## Topic Policy Columns

The static CSVs also include route-policy columns for clean topic scoring:

- `allowed_topics` lists runtime topics that count as correct for the row.
- `topic_policy` explains why alternate topics are allowed, for example `expected_topic_only`, `safety_guardrail_topic`, or `salesforce_sfcase_route`.
- `topic_policy_notes` captures the route decision in plain language.

Key route decisions encoded in the masters:

- Most rows remain strict: only `expected_topic` is allowed.
- Safety/privacy/injection rows may route to dedicated guardrail topics such as `Prompt_Injection`, `Reverse_Engineering`, `Inappropriate_Content`, or `Off_Topic`.
- Salesforce sfcase rows may route through `GeneralQnA_HelpIQ` or render through `Escalation` after the Salesforce subagent removal.
- `Salesforce_Support` is not an allowed topic in the current HelpIQ architecture.

Dynamic rows also carry `expected_topic`, `allowed_topics`, and `topic_policy` so report sub-agent comparisons do not need to infer routing from behavior category alone.
