#!/usr/bin/env python3
"""Build HelpIQ evaluation reports with the iterative report structure.

The report intentionally keeps static Testing Center results and dynamic preview
scenarios as separate tiers. Static rows have full benchmark/taxonomy/latency
fields. Dynamic rows have behavior and quality metrics, but not the same
Testing Center metric set or taxonomy dimensions.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from html import escape
from pathlib import Path
from statistics import mean, median
from typing import Any

METRIC_ALIASES = {
    "topic": ["topic_assertion", "topic_sequence_match"],
    "actions": ["actions_assertion", "action_assertion", "action_sequence_match"],
    "expected_answer": ["output_validation", "bot_response_rating"],
    "completeness": ["completeness"],
    "coherence": ["coherence"],
    "conciseness": ["conciseness"],
    "latency": ["output_latency_milliseconds"],
}
BENCHMARK_METRICS = ["topic", "actions", "expected_answer", "completeness", "coherence", "conciseness"]
DETERMINISTIC_METRICS = ["topic", "actions"]
RESPONSE_QUALITY_METRICS = ["coherence", "conciseness"]
ALIGNMENT_METRICS = ["expected_answer", "completeness"]
DYNAMIC_METRICS = ["expected_answer_alignment", "completeness", "coherence", "conciseness"]
COLORS = ["#16a34a", "#0891b2", "#7c3aed", "#2454d6"]
EVAL_ROOT = Path(__file__).resolve().parents[1]
MODE_LABELS = {
    "tier_balanced": "Tier-Balanced",
    "volume_weighted": "Volume-Weighted",
}


def load_json(path: Path | None) -> dict[str, Any] | None:
    if not path or not path.exists():
        return None
    raw = path.read_text()
    start = raw.find("{")
    if start < 0:
        return None
    return json.loads(raw[start:])


def load_master(path: Path | None) -> dict[int, dict[str, str]]:
    if not path or not path.exists():
        return {}
    with path.open(newline="") as f:
        rows = {}
        for index, row in enumerate(csv.DictReader(f), start=1):
            key = row.get("case_number") or index
            rows[int(key)] = row
        return rows


def load_dynamic_master(path: Path | None = None) -> dict[str, dict[str, str]]:
    path = path or EVAL_ROOT / "dynamic_tests.csv"
    if not path.exists():
        return {}
    with path.open(newline="") as f:
        return {row["scenario_id"]: row for row in csv.DictReader(f)}


def test_cases(data: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not data:
        return []
    if "testCases" in data:
        return data["testCases"]
    return data.get("result", {}).get("testCases", [])


def metric_result(tc: dict[str, Any], metric: str) -> dict[str, Any] | None:
    aliases = METRIC_ALIASES[metric]
    for result in tc.get("testResults", []):
        if result.get("name") in aliases or result.get("metricLabel") in aliases:
            return result
    return None


def metric_pass(tc: dict[str, Any], metric: str) -> bool | None:
    result = metric_result(tc, metric)
    if not result:
        return None
    value = str(result.get("result", "")).upper()
    return value in {"PASS", "PASSED"}


def metric_numeric(tc: dict[str, Any], metric: str) -> float | None:
    result = metric_result(tc, metric)
    if not result:
        return None
    for key in ("actualValue", "score", "value"):
        raw = result.get(key)
        if raw is None:
            continue
        try:
            return float(raw)
        except (TypeError, ValueError):
            continue
    return None


def rate_dict(passed: int, total: int) -> dict[str, Any]:
    return {"passed": passed, "total": total, "rate": round(passed / total * 100, 1) if total else None}


def average_rate(metrics: list[dict[str, Any]]) -> dict[str, Any]:
    scored = [item for item in metrics if item.get("rate") is not None]
    if not scored:
        return {"passed": 0, "total": 0, "rate": None}
    return {
        "passed": sum(item["passed"] for item in scored),
        "total": sum(item["total"] for item in scored),
        "rate": round(mean(item["rate"] for item in scored), 1),
    }


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    values = sorted(values)
    index = (len(values) - 1) * pct
    low = math.floor(index)
    high = math.ceil(index)
    if low == high:
        return values[int(index)]
    return values[low] * (high - index) + values[high] * (index - low)


def enrich_cases(cases: list[dict[str, Any]], master: dict[int, dict[str, str]], suite: str) -> list[dict[str, Any]]:
    enriched = []
    for tc in cases:
        number = int(tc.get("testNumber") or len(enriched) + 1)
        row = master.get(number, {})
        item = {
            "suite": suite,
            "test_number": number,
            "test_id": row.get("test_id") or f"{suite}-{number:04d}",
            "product": row.get("product") or "Unclassified",
            "category": row.get("category") or "Unclassified",
            "subcategory": row.get("subcategory") or "Unclassified",
            "expected_topic": row.get("expected_topic") or "Unspecified",
            "tool_policy": row.get("tool_policy") or "Unspecified",
            "topic_policy": row.get("topic_policy") or "Unspecified",
            "utterance": row.get("utterance") or tc.get("inputs", {}).get("utterance", ""),
            "case": tc,
        }
        enriched.append(item)
    return enriched


def summarize_static_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = {}
    for metric in BENCHMARK_METRICS:
        values = [metric_pass(row["case"], metric) for row in rows]
        scored = [value for value in values if value is not None]
        metrics[metric] = rate_dict(sum(1 for value in scored if value), len(scored))
    latencies = [value for row in rows if (value := metric_numeric(row["case"], "latency")) is not None]
    composites = {
        "benchmark": average_rate([metrics[name] for name in BENCHMARK_METRICS]),
        "deterministic": average_rate([metrics[name] for name in DETERMINISTIC_METRICS]),
        "response_quality": average_rate([metrics[name] for name in RESPONSE_QUALITY_METRICS]),
        "expected_answer_alignment": average_rate([metrics[name] for name in ALIGNMENT_METRICS]),
    }
    return {
        "total": len(rows),
        "metrics": metrics,
        "composites": composites,
        "latency": {
            "count": len(latencies),
            "avg": round(mean(latencies), 1) if latencies else None,
            "median": round(median(latencies), 1) if latencies else None,
            "p95": round(percentile(latencies, 0.95), 1) if latencies else None,
        },
    }


def summarize_group(rows: list[dict[str, Any]], key_fn: Any) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[key_fn(row)].append(row)
    out = []
    for name, group_rows in groups.items():
        summary = summarize_static_rows(group_rows)
        out.append({"name": name, "rows": len(group_rows), **summary})
    return sorted(out, key=lambda item: (-item["rows"], item["name"]))  # type: ignore[index]


def summarize_dynamic(data: dict[str, Any] | None) -> dict[str, Any]:
    empty = {
        "behavior": {"passed": 0, "total": 0, "rate": None},
        "quality_metrics": {},
        "failure_counts": {},
        "by_category": [],
        "by_strategy": [],
        "by_risk": [],
        "records": [],
    }
    if not data:
        return empty
    summary = data.get("summary", data if isinstance(data, dict) else {})
    records = data.get("records", []) if isinstance(data, dict) else []
    dynamic_master = load_dynamic_master()
    if not records and summary.get("behavior_by_scenario"):
        records = []
        for scenario_id, item in summary.get("behavior_by_scenario", {}).items():
            passed = int(item.get("passed", 0) or 0)
            total = int(item.get("total", 0) or 0)
            for index in range(total):
                records.append({
                    "scenario_id": scenario_id,
                    "run": index + 1,
                    "passed": index < passed,
                    "failures": [] if index < passed else ["behavior_failure"],
                })
    for record in records:
        master_row = dynamic_master.get(str(record.get("scenario_id") or ""), {})
        # Treat the canonical dynamic CSV as the source of truth. Older dynamic
        # result files reused `category` for scenario category, which breaks
        # taxonomy joins unless we overwrite it here.
        for field in (
            "product",
            "category",
            "subcategory",
            "scenario_category",
            "risk",
            "summary",
            "expected_behavior",
            "expected_topic",
            "allowed_topics",
            "topic_policy",
            "tool_policy",
            "allowed_tools",
            "forbidden_tools",
            "requires_confirmation_before_tool",
        ):
            if master_row.get(field):
                record[field] = master_row[field]
    behavior = rate_dict(int(summary.get("passed_runs", summary.get("behavior_passed", 0)) or 0), int(summary.get("total_runs", summary.get("behavior_total", 0)) or 0))
    quality = {}
    for name, item in (summary.get("quality_metrics", {}) or {}).items():
        passed = int(item.get("passed", 0) or 0)
        total = int(item.get("total", 0) or 0)
        quality[name] = rate_dict(passed, total)
    failure_counts = summary.get("behavior_failure_counts", summary.get("failure_counts", {}))

    def dynamic_groups(field: str) -> list[dict[str, Any]]:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for record in records:
            grouped[str(record.get(field) or "Unclassified")].append(record)
        rows = []
        for name, group in grouped.items():
            passed = sum(1 for record in group if record.get("passed"))
            rows.append({"name": name, **rate_dict(passed, len(group))})
        return sorted(rows, key=lambda row: (-row["total"], row["name"]))

    def dynamic_taxonomy_groups() -> list[dict[str, Any]]:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for record in records:
            key = " / ".join(
                [
                    str(record.get("product") or "Unclassified"),
                    str(record.get("category") or "Unclassified"),
                    str(record.get("subcategory") or "Unclassified"),
                ]
            )
            grouped[key].append(record)
        rows = []
        for name, group in grouped.items():
            passed = sum(1 for record in group if record.get("passed"))
            rows.append({"name": name, **rate_dict(passed, len(group))})
        return sorted(rows, key=lambda row: (-row["total"], row["name"]))

    return {
        "behavior": behavior,
        "quality_metrics": quality,
        "failure_counts": failure_counts,
        "by_category": dynamic_groups("scenario_category"),
        "by_taxonomy": dynamic_taxonomy_groups(),
        "by_strategy": dynamic_groups("strategy"),
        "by_risk": dynamic_groups("risk"),
        "records": records,
    }


def pct(metric: dict[str, Any]) -> str:
    if not metric or metric.get("rate") is None:
        return "-"
    return f"{metric['passed']}/{metric['total']} ({metric['rate']:.1f}%)"


def score_metric(rate: float | None, label: str) -> dict[str, Any]:
    return {"passed": 0, "total": 0, "rate": rate, "label": label}


def evaluated_score_modes(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    single = payload["single_turn"]["composites"]["benchmark"]
    fixed = payload["fixed_multi_turn"]["composites"]["benchmark"]
    static_total = payload["static_total"]["composites"]["benchmark"]
    dynamic = payload["dynamic"]["behavior"]
    tier_rates = [item["rate"] for item in [single, fixed, dynamic] if item.get("rate") is not None]
    tier_balanced = {
        "label": "Tier-Balanced",
        "rate": round(mean(tier_rates), 1) if tier_rates else None,
        "count": "1/3 single-turn + 1/3 fixed multi-turn + 1/3 dynamic",
        "notes": "Best release-risk view. Prevents 999 single-turn cases from hiding multi-turn or dynamic regressions.",
    }
    volume_passed = static_total["passed"] + dynamic.get("passed", 0)
    volume_total = static_total["total"] + dynamic.get("total", 0)
    volume_weighted = {
        "label": "Volume-Weighted",
        **rate_dict(volume_passed, volume_total),
        "count": f"{volume_passed}/{volume_total}",
        "notes": "Every static benchmark metric check and every dynamic behavior run count equally.",
    }
    return {"tier_balanced": tier_balanced, "volume_weighted": volume_weighted}


def metric_for_mode(agent: dict[str, Any], metric: str, mode: str) -> dict[str, Any]:
    dynamic = agent["dynamic"]["behavior"]
    if mode == "tier_balanced":
        if metric == "benchmark":
            rates = [
                agent["single_turn"]["composites"]["benchmark"]["rate"],
                agent["fixed_multi_turn"]["composites"]["benchmark"]["rate"],
                dynamic["rate"],
            ]
            rates = [rate for rate in rates if rate is not None]
            return {
                "rate": round(mean(rates), 1) if rates else None,
                "count": "1/3 static single + 1/3 fixed multi + 1/3 dynamic",
            }
        if metric in {"deterministic", "response_quality", "expected_answer_alignment"}:
            rates = [
                agent["single_turn"]["composites"][metric]["rate"],
                agent["fixed_multi_turn"]["composites"][metric]["rate"],
            ]
            rates = [rate for rate in rates if rate is not None]
            return {"rate": round(mean(rates), 1) if rates else None, "count": "50/50 single + fixed static"}
    if mode == "volume_weighted":
        if metric == "benchmark":
            static = agent["static_total"]["composites"]["benchmark"]
            passed = static["passed"] + dynamic.get("passed", 0)
            total = static["total"] + dynamic.get("total", 0)
            item = rate_dict(passed, total)
            return {"rate": item["rate"], "count": f"{passed}/{total}"}
        if metric in {"deterministic", "response_quality", "expected_answer_alignment"}:
            item = agent["static_total"]["composites"][metric]
            return {"rate": item["rate"], "count": f"{item['passed']}/{item['total']}"}
    if metric == "dynamic":
        return {"rate": dynamic["rate"], "count": f"{dynamic.get('passed', 0)}/{dynamic.get('total', 0)}"}
    return {"rate": None, "count": "-"}


def dynamic_taxonomy_map(payload: dict[str, Any]) -> dict[tuple[str, str, str], dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in payload["dynamic"].get("records", []):
        key = (
            str(record.get("product") or "Unclassified"),
            str(record.get("category") or "Unclassified"),
            str(record.get("subcategory") or "Unclassified"),
        )
        grouped[key].append(record)
    return {
        key: rate_dict(sum(1 for record in records if record.get("passed")), len(records))
        for key, records in grouped.items()
    }


def static_taxonomy_map(payload: dict[str, Any]) -> dict[tuple[str, str, str], dict[str, Any]]:
    out = {}
    for item in payload["by_taxonomy"]:
        product, category, subcategory = item["name"].split("|||")
        out[(product, category, subcategory)] = item
    return out


def taxonomy_benchmark_for_mode(static_item: dict[str, Any] | None, dynamic_item: dict[str, Any] | None, mode: str) -> float | None:
    static_benchmark = (static_item or {}).get("composites", {}).get("benchmark", {})
    static_rate = static_benchmark.get("rate")
    dynamic_rate = (dynamic_item or {}).get("rate")
    if mode == "tier_balanced":
        rates = [rate for rate in (static_rate, dynamic_rate) if rate is not None]
        return round(mean(rates), 1) if rates else None
    if mode == "volume_weighted":
        static_passed = int(static_benchmark.get("passed", 0) or 0)
        static_total = int(static_benchmark.get("total", 0) or 0)
        dynamic_passed = int((dynamic_item or {}).get("passed", 0) or 0)
        dynamic_total = int((dynamic_item or {}).get("total", 0) or 0)
        return rate_dict(static_passed + dynamic_passed, static_total + dynamic_total)["rate"]
    return None


def dynamic_expected_subagent(record: dict[str, Any]) -> str:
    if record.get("expected_topic"):
        return str(record["expected_topic"])
    scenario_id = str(record.get("scenario_id") or "")
    scenario_category = str(record.get("scenario_category") or "")
    scenario_specific = {
        "cross_topic_qna_to_figma_access": "HelpIqAgentMultiplierSoftwareRequests",
    }
    if scenario_id in scenario_specific:
        return scenario_specific[scenario_id]
    category_map = {
        "salesforce_sfcase": "Escalation",
        "human_handoff": "Escalation",
        "direct_it_ticket_intake": "Escalation",
        "software_access": "HelpIqAgentMultiplierSoftwareRequests",
        "qna_followup_failure": "GeneralQnA_HelpIQ",
        "ambiguous_clarification": "GeneralQnA_HelpIQ",
        "safety_privacy": "Prompt_Injection",
        "capability_offtopic": "GeneralQnA_HelpIQ",
        "cross_topic_recovery": "GeneralQnA_HelpIQ",
    }
    return category_map.get(scenario_category, "GeneralQnA_HelpIQ")


def dynamic_subagent_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in payload["dynamic"].get("records", []):
        grouped[dynamic_expected_subagent(record)].append(record)
    return {
        name: rate_dict(sum(1 for record in records if record.get("passed")), len(records))
        for name, records in grouped.items()
    }


def fmt_rate(value: float | None) -> str:
    return "-" if value is None else f"{value:.1f}%"


def fmt_ms(value: float | None) -> str:
    return "-" if value is None else f"{value:,.0f} ms"


def bar(width: float | None, color: str) -> str:
    width = max(0, min(100, width or 0))
    return f"<div class='bar-track'><div class='bar-fill' style='width:{width:.1f}%;background:{color}'></div></div>"


def metric_card(
    title: str,
    items: list[dict[str, Any]],
    value_fn: Any,
    count_fn: Any,
    tip: str = "",
    headline_label: str | None = None,
    baseline_label: str | None = None,
) -> str:
    rows = []
    baseline_item = next((item for item in items if item.get("label") == baseline_label), items[0] if items else None)
    baseline_rate = value_fn(baseline_item) if baseline_item else None
    for index, item in enumerate(items):
        value = value_fn(item)
        delta = "-" if value is None or baseline_rate is None else f"{value - baseline_rate:+.1f}pp"
        color = COLORS[index % len(COLORS)]
        rows.append(
            f"<div class='bar-row'><div class='bar-label'>{escape(item['label'])}</div>{bar(value, color)}"
            f"<div class='bar-value'>{fmt_rate(value)}</div><div class='bar-count'>{escape(count_fn(item))}</div><div class='bar-delta'>{escape(delta)}</div></div>"
        )
    headline_item = next((item for item in items if item.get("label") == headline_label), items[0] if items else None)
    headline = value_fn(headline_item) if headline_item else None
    tip_html = f"<span class='info-tip' tabindex='0' data-tip='{escape(tip)}'>i</span>" if tip else ""
    return (
        "<article class='metric-card'>"
        f"<div class='metric-card-head'><span class='label'>{escape(title)}</span>{tip_html}</div>"
        f"<div class='metric-headline'><span class='value'>{fmt_rate(headline)}</span></div>"
        f"<div class='bars'>{''.join(rows)}</div></article>"
    )


def table(headers: list[str], rows: list[list[str]], css_class: str = "") -> str:
    head = "".join(f"<th>{escape(header)}</th>" for header in headers)
    body = "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows)
    return f"<div class='table-wrap'><table class='{escape(css_class)}'><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>"


def sortable_table(headers: list[tuple[str, bool]], rows: list[list[str]], css_class: str = "") -> str:
    head_parts = []
    for index, (header, sortable) in enumerate(headers):
        if sortable:
            head_parts.append(
                f"<th class='sortable-col' data-sort-col='{index}' data-sort-type='number'>"
                f"{escape(header)} <span class='sort-indicator'>&#x2195;</span></th>"
            )
        else:
            head_parts.append(f"<th>{escape(header)}</th>")
    head = "".join(head_parts)
    body = "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows)
    return f"<div class='table-wrap'><table class='{escape(css_class)}'><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>"


def setup_section(agents: list[dict[str, Any]], primary_label: str, baseline_label: str) -> str:
    rows = []
    for agent in agents:
        static_rows = agent["static_rows"]
        products = {row["product"] for row in static_rows if row["product"] != "Unclassified"}
        categories = {row["category"] for row in static_rows if row["category"] != "Unclassified"}
        subcategories = {row["subcategory"] for row in static_rows if row["subcategory"] != "Unclassified"}
        topics = {row["expected_topic"] for row in static_rows if row["expected_topic"] != "Unspecified"}
        policies = Counter(row["tool_policy"] for row in static_rows)
        role = []
        if agent["agent"] == baseline_label:
            role.append("Baseline")
        if agent["agent"] == primary_label:
            role.append("Evaluated")
        dynamic_total = agent["dynamic"]["behavior"].get("total", 0) or 0
        rows.append([
            escape(agent["agent"]),
            ", ".join(role) or "Reference",
            str(agent["single_turn"]["total"]),
            str(agent["fixed_multi_turn"]["total"]),
            str(dynamic_total),
            str(len(topics)),
            f"{len(products)} / {len(categories)} / {len(subcategories)}",
            str(len(policies)),
        ])
    return f"""
<h2 class='section-heading'>Setup</h2>
<section class='panel'>
  <p class='hint'>Coverage and context only — no pass rates or score results. Baseline anchors percentage-point deltas in Results sections; evaluated agent anchors the headline and recommendation.</p>
  {table(['Agent', 'Role', 'Single-turn', 'Fixed Multi-turn', 'Dynamic Runs', 'Expected Topics', 'Products / Categories / Subcategories', 'Tool Policies'], rows)}
</section>
"""


def score_mode_control() -> str:
    return f"""
<div class='score-mode-floating' aria-label='Score mode selector'>
  <div class='score-mode-floating-title'>Score Mode <span class='info-tip' tabindex='0' data-tip='Tier-Balanced: weights single-turn static benchmark, fixed multi-turn static benchmark, and dynamic behavior equally. Volume-Weighted: counts every static benchmark metric check and dynamic behavior run equally.'>i</span></div>
  <div class='score-mode-toggle' role='group' aria-label='Score mode'>
    <button type='button' class='score-mode-button active' data-score-mode='tier_balanced'>Tier-Balanced</button>
    <button type='button' class='score-mode-button' data-score-mode='volume_weighted'>Volume-Weighted</button>
  </div>
</div>
"""


def score_mode_metric_card(
    title: str,
    agents: list[dict[str, Any]],
    metric: str,
    mode: str,
    tip: str,
    primary_label: str,
    baseline_label: str,
) -> str:
    items = []
    for agent in agents:
        item = metric_for_mode(agent, metric, mode)
        items.append({"label": agent["agent"], "rate": item["rate"], "count": item["count"]})
    return metric_card(title, items, lambda x: x["rate"], lambda x: x["count"], tip, primary_label, baseline_label)


def comparison_summary_section(agents: list[dict[str, Any]], primary_label: str, baseline_label: str) -> str:
    mode_sections = []
    for mode, label in MODE_LABELS.items():
        hidden = "" if mode == "tier_balanced" else " hidden-view"
        mode_sections.append(
            f"<div class='score-mode-view{hidden}' data-score-view='{mode}'>"
            f"<div class='panel-title'>Results - Summary ({escape(label)} mode)</div>"
            "<div class='metric-card-grid'>"
            + score_mode_metric_card(
                "Benchmark Score",
                agents,
                "benchmark",
                mode,
                "Changes with selected score mode. Tier-balanced weights tiers equally; volume-weighted counts every static check and dynamic run.",
                primary_label,
                baseline_label,
            )
            + score_mode_metric_card(
                "Deterministic Score",
                agents,
                "deterministic",
                mode,
                "Topic and action assertions. Dynamic has no equivalent deterministic assertion, so tier-balanced uses single/fixed static tiers.",
                primary_label,
                baseline_label,
            )
            + score_mode_metric_card(
                "Response Quality",
                agents,
                "response_quality",
                mode,
                "Coherence and conciseness. Dynamic quality proxies are not included because they are not Testing Center LLM judges.",
                primary_label,
                baseline_label,
            )
            + score_mode_metric_card(
                "Expected-Answer Alignment",
                agents,
                "expected_answer_alignment",
                mode,
                "Output validation and completeness. Dynamic expected-answer proxy is not included in static judge scoring.",
                primary_label,
                baseline_label,
            )
            + score_mode_metric_card(
                "Dynamic Behavior",
                agents,
                "dynamic",
                mode,
                "Scenario-level dynamic behavior pass rate. Shown for all modes for visibility; only included in Benchmark Score for tier-balanced and volume-weighted modes.",
                primary_label,
                baseline_label,
            )
            + "</div></div>"
        )
    return f"""
<h2 class='section-heading first'>Results - Summary</h2>
<section class='result-summary'>{''.join(mode_sections)}</section>
"""


def summary_section(payload: dict[str, Any]) -> str:
    tiers = [
        {"label": "Single-turn", **payload["single_turn"]},
        {"label": "Fixed multi-turn", **payload["fixed_multi_turn"]},
        {"label": "Static combined", **payload["static_total"]},
    ]
    dynamic_item = {"label": "Dynamic multi-turn", "behavior": payload["dynamic"]["behavior"]}
    return f"""
<h2 class='section-heading first'>Results - Summary</h2>
<section class='result-summary'><div class='metric-card-grid'>
{metric_card('Benchmark Score (static composite)', tiers, lambda x: x['composites']['benchmark']['rate'], lambda x: pct(x['composites']['benchmark']), 'Equal-weighted mean of topic, actions, expected answer, completeness, coherence, and conciseness for static Testing Center rows.')}
{metric_card('Deterministic Score', tiers, lambda x: x['composites']['deterministic']['rate'], lambda x: pct(x['composites']['deterministic']), 'Mean of topic and action assertions.')}
{metric_card('Response Quality', tiers, lambda x: x['composites']['response_quality']['rate'], lambda x: pct(x['composites']['response_quality']), 'Mean of coherence and conciseness.')}
{metric_card('Expected-Answer Alignment', tiers, lambda x: x['composites']['expected_answer_alignment']['rate'], lambda x: pct(x['composites']['expected_answer_alignment']), 'Mean of output validation and completeness.')}
{metric_card('Dynamic Behavior', [dynamic_item], lambda x: x['behavior']['rate'], lambda x: pct(x['behavior']), 'Dynamic preview behavior is reported separately because it has scenario-level pass/fail instead of Testing Center topic/action metrics.')}
</div></section>
"""


def recommendation_section(agents: list[dict[str, Any]], primary_label: str, baseline_label: str) -> str:
    primary = next(agent for agent in agents if agent["agent"] == primary_label)
    mode_sections = []
    for mode, label in MODE_LABELS.items():
        primary_benchmark = metric_for_mode(primary, "benchmark", mode)["rate"] or 0
        action = primary["static_total"]["metrics"]["actions"]["rate"] or 0
        dynamic = primary["dynamic"]["behavior"]["rate"]
        if dynamic is None:
            verdict = "Static ready; dynamic pending"
            note = "Dynamic preview results were not included for the evaluated agent."
        elif primary_benchmark >= 85 and action >= 75 and dynamic >= 95:
            verdict = "Proceed to failure review"
            note = "The selected score-mode readout is acceptable for review; inspect fixed multi-turn tool-action failures before release."
        else:
            verdict = "Review before release"
            note = "At least one selected-mode or support metric is below the current review threshold."
        rows = []
        baseline_metric = metric_for_mode(next(agent for agent in agents if agent["agent"] == baseline_label), "benchmark", mode)["rate"]
        for agent in agents:
            benchmark = metric_for_mode(agent, "benchmark", mode)
            deterministic = metric_for_mode(agent, "deterministic", mode)
            delta = "-" if benchmark["rate"] is None or baseline_metric is None else f"{benchmark['rate'] - baseline_metric:+.1f}pp"
            rows.append([
                escape(agent["agent"]),
                fmt_rate(benchmark["rate"]),
                escape(benchmark["count"]),
                fmt_rate(deterministic["rate"]),
                pct(agent["dynamic"]["behavior"]),
                escape(delta),
            ])
        hidden = "" if mode == "tier_balanced" else " hidden-view"
        mode_sections.append(
            f"<div class='score-mode-view{hidden}' data-score-view='{mode}'>"
            f"<div class='recommendation-grid'><div class='recommendation-card note-card'><div class='label'>Verdict ({escape(label)} mode)</div>"
            f"<p class='verdict'>{escape(verdict)}</p><p>{escape(note)}</p></div>"
            "<div class='recommendation-card'><div class='label'>Readout</div>"
            f"<p>Baseline: <strong>{escape(baseline_label)}</strong>. Evaluated agent: <strong>{escape(primary_label)}</strong>. This table uses the same selected-mode benchmark formula as Results - Summary.</p>"
            "<p class='hint'>Static Actions remains visible because fixed multi-turn tool-action failures are release-relevant even when the headline score is acceptable.</p></div></div>"
            + table(["Agent", "Mode Benchmark", "Mode Count / Formula", "Deterministic", "Dynamic Behavior", "Delta vs Baseline"], rows)
            + "</div>"
        )
    return "<section class='recommendation-panel'><div class='panel-title'>Recommendation</div>" + "".join(mode_sections) + "</section>"


def breakdown_section(agents: list[dict[str, Any]], primary_label: str, baseline_label: str) -> str:
    metric_labels = {
        "topic": "Topic Assertion",
        "actions": "Tool Action Use",
        "expected_answer": "Output Validation",
        "completeness": "Completeness",
        "coherence": "Coherence",
        "conciseness": "Conciseness",
    }
    items = [{"label": agent["agent"], **agent["static_total"]} for agent in agents]
    sections = []
    for title, metrics in [
        ("Deterministic Score Breakdown (Static Testing Center Only)", DETERMINISTIC_METRICS),
        ("Response Quality Breakdown (Static Testing Center Only)", RESPONSE_QUALITY_METRICS),
        ("Expected-Answer Alignment Breakdown (Static Testing Center Only)", ALIGNMENT_METRICS),
    ]:
        cards = [
            metric_card(
                metric_labels[metric],
                items,
                lambda x, m=metric: x["metrics"][m]["rate"],
                lambda x, m=metric: pct(x["metrics"][m]),
                "Static Testing Center metric; not affected by the score-mode toggle.",
                primary_label,
                baseline_label,
            )
            for metric in metrics
        ]
        sections.append("<section class='result-summary'><div class='panel-title'>" + escape(title) + "</div><div class='metric-card-grid'>" + "".join(cards) + "</div></section>")
    dynamic_items = [{"label": agent["agent"], "dynamic": agent["dynamic"]} for agent in agents]
    dynamic_metric_labels = {
        "expected_answer_alignment": "Expected Answer Alignment",
        "completeness": "Completeness",
        "coherence": "Coherence",
        "conciseness": "Conciseness",
    }
    dynamic_cards = [
        metric_card(
            "Dynamic Behavior",
            dynamic_items,
            lambda x: x["dynamic"]["behavior"]["rate"],
            lambda x: pct(x["dynamic"]["behavior"]),
            "Scenario-level dynamic preview behavior pass rate; not affected by the score-mode toggle.",
            primary_label,
            baseline_label,
        ),
        *[
            metric_card(
                dynamic_metric_labels[metric],
                dynamic_items,
                lambda x, m=metric: (x["dynamic"]["quality_metrics"].get(m) or {}).get("rate"),
                lambda x, m=metric: pct(x["dynamic"]["quality_metrics"].get(m) or {}),
                "Dynamic quality proxy derived from scenario outcome and response shape; not a Testing Center LLM judge.",
                primary_label,
                baseline_label,
            )
            for metric in DYNAMIC_METRICS
        ],
    ]
    sections.append(
        "<section class='result-summary'><div class='panel-title'>Dynamic Breakdown</div><div class='metric-card-grid'>"
        + "".join(dynamic_cards)
        + "</div></section>"
    )
    return f"<h2>Benchmark Breakdown</h2>{''.join(sections)}"


def latency_section(agents: list[dict[str, Any]]) -> str:
    rows = []
    for agent in agents:
        for label, summary in [("Single-turn", agent["single_turn"]), ("Fixed multi-turn", agent["fixed_multi_turn"]), ("Static combined", agent["static_total"])]:
            latency = summary["latency"]
            rows.append([escape(agent["agent"]), escape(label), str(latency["count"]), fmt_ms(latency["avg"]), fmt_ms(latency["median"]), fmt_ms(latency["p95"])])
    return "<section class='result-summary'><div class='panel-title'>Output Latency (Static Testing Center Only)</div>" + table(["Agent", "Tier", "Scored", "Average", "Median", "P95"], rows) + "</section>"


def subagent_benchmark(agent: dict[str, Any], name: str, mode: str) -> float | None:
    static_items = {item["name"]: item for item in agent["by_subagent"]}
    dynamic_items = dynamic_subagent_map(agent)
    static_item = static_items.get(name)
    dynamic_item = dynamic_items.get(name)
    if not static_item and not dynamic_item:
        return None
    return taxonomy_benchmark_for_mode(static_item, dynamic_item, mode)


def subagent_cell(value: float | None, delta: str) -> str:
    if value is None:
        return "-"
    return (
        f"<div class='subagent-benchmark'>{fmt_rate(value)}</div>"
        f"<div class='subagent-delta'>{escape(delta)}</div>"
    )


def subagent_section(agents: list[dict[str, Any]], baseline_label: str) -> str:
    names = sorted(set().union(*[
        set(item["name"] for item in agent["by_subagent"]) | set(dynamic_subagent_map(agent))
        for agent in agents
    ]))
    baseline_agent = next((agent for agent in agents if agent["agent"] == baseline_label), agents[0])
    mode_tables = []
    for mode, label in MODE_LABELS.items():
        baseline_rates = {name: subagent_benchmark(baseline_agent, name, mode) for name in names}
        rows = []
        for agent in agents:
            is_baseline = agent["agent"] == baseline_label
            row = [escape(agent["agent"])]
            for name in names:
                value = subagent_benchmark(agent, name, mode)
                baseline_value = baseline_rates.get(name)
                if is_baseline:
                    delta = "0.0pp" if value is not None else "-"
                elif value is None or baseline_value is None:
                    delta = "-"
                else:
                    delta = f"{value - baseline_value:+.1f}pp"
                row.append(subagent_cell(value, delta))
            rows.append(row)
        hidden = "" if mode == "tier_balanced" else " hidden-view"
        mode_tables.append(
            f"<div class='score-mode-view{hidden}' data-score-view='{mode}'>"
            f"<div class='panel-title'>Benchmark by Sub-Agent ({escape(label)} mode)</div>"
            "<p class='hint'>Pivot by expected sub-agent. Each cell shows the selected score-mode benchmark "
            "(tier-balanced averages static+dynamic rates; volume-weighted sums passed/total) and the "
            f"percentage-point delta vs baseline <strong>{escape(baseline_label)}</strong> for that slice.</p>"
            + table(["Agent", *names], rows)
            + "</div>"
        )
    return "<section class='result-summary'>" + "".join(mode_tables) + "</section>"


def taxonomy_section(agents: list[dict[str, Any]], baseline_label: str) -> str:
    keys = sorted(set().union(*[
        set(static_taxonomy_map(agent)) | set(dynamic_taxonomy_map(agent))
        for agent in agents
    ]))
    baseline = next((agent for agent in agents if agent["agent"] == baseline_label), agents[0])
    baseline_static = static_taxonomy_map(baseline)
    baseline_dynamic = dynamic_taxonomy_map(baseline)
    mode_tables = []
    for mode, label in MODE_LABELS.items():
        rows = []
        for agent in agents:
            static_items = static_taxonomy_map(agent)
            dynamic_items = dynamic_taxonomy_map(agent)
            for product, category, subcategory in keys:
                static_item = static_items.get((product, category, subcategory))
                dynamic_item = dynamic_items.get((product, category, subcategory))
                if not static_item and not dynamic_item:
                    continue
                rate = taxonomy_benchmark_for_mode(static_item, dynamic_item, mode)
                baseline_rate = taxonomy_benchmark_for_mode(
                    baseline_static.get((product, category, subcategory)),
                    baseline_dynamic.get((product, category, subcategory)),
                    mode,
                )
                if rate is None or baseline_rate is None or agent["agent"] == baseline_label:
                    delta = "-" if agent["agent"] != baseline_label else "0.0pp"
                    delta_value = "" if agent["agent"] != baseline_label else "0"
                else:
                    diff = rate - baseline_rate
                    delta = f"{diff:+.1f}pp"
                    delta_value = f"{diff:.4f}"
                rate_value = "" if rate is None else f"{rate:.4f}"
                rows.append([
                    escape(agent["agent"]),
                    escape(product),
                    escape(category),
                    escape(subcategory),
                    str((static_item or {}).get("rows", 0)),
                    str((dynamic_item or {}).get("total", 0)),
                    f"<span data-sort='{rate_value}'>{fmt_rate(rate)}</span>",
                    f"<span data-sort='{delta_value}'>{escape(delta)}</span>",
                ])
        hidden = "" if mode == "tier_balanced" else " hidden-view"
        mode_tables.append(
            f"<div class='score-mode-view{hidden}' data-score-view='{mode}'>"
            f"<div class='panel-title'>Benchmark by Product x Category x Subcategory ({escape(label)} mode)</div>"
            "<p class='hint'>Click <strong>Mode Benchmark</strong> or <strong>Delta vs Baseline</strong> to sort. Click again to toggle direction.</p>"
            "<details class='detail-toggle' open><summary><span class='show-label'>Show taxonomy mix</span><span class='hide-label'>Hide taxonomy mix</span></summary>"
            + sortable_table(
                [
                    ("Agent", False),
                    ("Product", False),
                    ("Category", False),
                    ("Subcategory", False),
                    ("Static Rows", False),
                    ("Dynamic Runs", False),
                    ("Mode Benchmark", True),
                    ("Delta vs Baseline", True),
                ],
                rows,
                css_class="sortable",
            )
            + "</details></div>"
        )
    return (
        "<section class='result-summary'>"
        + "".join(mode_tables)
        + "</section>"
    )


def dynamic_section(agents: list[dict[str, Any]]) -> str:
    quality_rows = []
    category_rows = []
    taxonomy_rows = []
    strategy_rows = []
    risk_rows = []
    failure_rows = []
    for agent in agents:
        dynamic = agent["dynamic"]
        q = dynamic.get("quality_metrics", {})
        for metric in DYNAMIC_METRICS:
            quality_rows.append([escape(agent["agent"]), escape(metric.replace("_", " ").title()), pct(q.get(metric, {}))])
        category_rows.extend([[escape(agent["agent"]), escape(row["name"]), pct(row)] for row in dynamic["by_category"]])
        taxonomy_rows.extend([[escape(agent["agent"]), escape(row["name"]), pct(row)] for row in dynamic.get("by_taxonomy", [])])
        strategy_rows.extend([[escape(agent["agent"]), escape(row["name"]), pct(row)] for row in dynamic["by_strategy"]])
        risk_rows.extend([[escape(agent["agent"]), escape(row["name"]), pct(row)] for row in dynamic.get("by_risk", [])])
        failure_rows.append([escape(agent["agent"]), f"<code>{escape(json.dumps(dynamic.get('failure_counts', {}), sort_keys=True))}</code>"])
    explainer = """
<div class='coverage-card'>
  <div class='coverage-name'>What Dynamic Behavior Tests</div>
  <p class='hint'>Scenario-level multi-turn behavior: Salesforce sfcase fallback, human-handoff gating, direct IT ticket intake/confirmation, QnA follow-up recovery, ambiguous clarification, software-access collection/confirmation, safety/privacy refusal, off-topic handling, and cross-topic recovery.</p>
  <p class='hint'><strong>Not a static judge substitute:</strong> dynamic quality rows are lightweight proxies derived from behavior/result shape. They are not the same as Testing Center response-quality or expected-answer LLM judges.</p>
</div>
"""
    return (
        "<section class='result-summary'><div class='panel-title'>Dynamic Tier Breakdown</div>"
        + explainer
        + table(["Agent", "Quality Metric", "Pass Rate"], quality_rows)
        + table(["Agent", "Dynamic Scenario Category", "Behavior Pass Rate"], category_rows)
        + table(["Agent", "Dynamic Product / Category / Subcategory", "Behavior Pass Rate"], taxonomy_rows)
        + table(["Agent", "Dynamic Strategy", "Behavior Pass Rate"], strategy_rows)
        + table(["Agent", "Dynamic Risk", "Behavior Pass Rate"], risk_rows)
        + table(["Agent", "Behavior Failures"], failure_rows)
        + "</section>"
    )


def known_gaps_section() -> str:
    return """
<h2>Known Gaps</h2>
<ul>
  <li><strong>Dynamic coverage is thinner than static coverage</strong> - dynamic rows now have canonical taxonomy and expected-topic mapping, but only cover 69 behavior runs.</li>
  <li><strong>Dynamic latency is not captured</strong> - the preview runner does not currently record per-turn latency, so the latency section is static-only.</li>
  <li><strong>Some sections remain static-only</strong> - latency has no dynamic equivalent. Sub-agent and taxonomy benchmarks compare all agent versions and change by score mode where dynamic mapping data exists.</li>
  <li><strong>LLM judge variance still applies</strong> - expected-answer and quality metrics should be read with qualitative samples for high-risk regressions.</li>
</ul>
"""


def guide() -> str:
    return """
<h2>Report Guide</h2>
<p>This report restores the original iterative report structure while using explicit baseline/evaluated agent roles and clean HelpIQ evaluation inputs.</p>
<h3>Sections</h3>
<ul>
  <li><strong>Setup</strong>: coverage and context only — test counts, taxonomy dimensions, expected topics, tool-policy counts, and explicit baseline/evaluated roles. No pass rates or score results.</li>
  <li><strong>Score Mode control</strong>: fixed selector under Report Guide for tier-balanced and volume-weighted summary readouts.</li>
  <li><strong>Results - Summary</strong>: cards update based on the selected score mode, with dynamic behavior shown for visibility in every mode.</li>
  <li><strong>Recommendation</strong>: release-readiness readout using the same selected score-mode formulas as the summary.</li>
  <li><strong>Benchmark Breakdown</strong>: all-agent static Testing Center deterministic, response-quality, and expected-answer component metrics, plus a Dynamic Breakdown panel for behavior and quality-proxy metrics.</li>
  <li><strong>Latency, Sub-Agent, Taxonomy</strong>: latency stays all-agent static-only. Sub-agent benchmark is a pivot table (agents as rows, expected sub-agents as columns) with score-mode benchmark and baseline delta per cell. Taxonomy benchmarks compare all agents and update by score mode where dynamic mapping data exists.</li>
</ul>
<h3>Why dynamic is separate</h3>
<p>Dynamic scenarios are preview runs with deterministic behavior checks. They test multi-turn flow outcomes such as no premature IT ticket creation, Salesforce case-link fallback, confirmation gates, privacy refusals, cross-topic recovery, and software-access collection before submission.</p>
<p>Dynamic behavior is <strong>not</strong> a full response-quality or expected-answer-alignment judge. The dynamic runner records lightweight quality proxies, but those are rule-derived from the scenario outcome and response shape, not the same Testing Center LLM judge metrics used for static <code>output_validation</code>, <code>completeness</code>, <code>coherence</code>, and <code>conciseness</code>.</p>
"""


def html_report(payload: dict[str, Any]) -> str:
    agents = payload.get("agents") or [payload]
    primary_label = payload.get("primary_agent")
    baseline_label = payload.get("baseline_agent") or agents[0]["agent"]
    primary = next((agent for agent in agents if agent["agent"] == primary_label), agents[0])
    for agent in agents:
        agent["_primary_agent"] = primary["agent"]
        agent["_baseline_agent"] = baseline_label
    cards = "".join(
        f"<div class='version-card'><span class='version-color' style='background:{COLORS[index % len(COLORS)]}'></span>"
        f"<div class='version-info'><strong>{escape(agent['agent'])}</strong>"
        f"<div class='version-meta'>Static {agent['static_total']['total']} · Dynamic {agent['dynamic']['behavior']['passed']}/{agent['dynamic']['behavior']['total']}</div></div></div>"
        for index, agent in enumerate(agents)
    )
    detail_note = f"<p class='subtitle'>Baseline: <strong>{escape(baseline_label)}</strong>. Evaluated agent: <strong>{escape(primary['agent'])}</strong>. All comparison sections include every agent version; static-only sections are labeled.</p>"
    return f"""<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><title>HelpIQ Evaluation Report</title><style>{STYLES}</style></head>
<body><div class='floating-controls'><button class='guide-toggle' type='button' onclick="document.body.classList.toggle('guide-open')">Report Guide</button>{score_mode_control()}</div>
<aside class='guide-panel'><button class='guide-close' onclick="document.body.classList.remove('guide-open')">Hide</button><div class='guide-content'>{guide()}</div></aside>
<main>
<h1>HelpIQ Evaluation Report</h1>
<p class='subtitle'>Unified static and dynamic report generated from policy-corrected HelpIQ results.</p>
<section class='versions-legend-wrap'><div class='panel-title'>Versions in this report</div><div class='versions-legend'>{cards}</div></section>
{detail_note}
{setup_section(agents, primary['agent'], baseline_label)}
{comparison_summary_section(agents, primary['agent'], baseline_label)}
{recommendation_section(agents, primary['agent'], baseline_label)}
{breakdown_section(agents, primary['agent'], baseline_label)}
{latency_section(agents)}
{subagent_section(agents, baseline_label)}
{taxonomy_section(agents, baseline_label)}
{dynamic_section(agents)}
{known_gaps_section()}
</main>
<script>
document.querySelectorAll('[data-score-mode]').forEach((button) => {{
  button.addEventListener('click', () => {{
    const mode = button.getAttribute('data-score-mode');
    document.querySelectorAll('[data-score-mode]').forEach((b) => b.classList.toggle('active', b === button));
    document.querySelectorAll('[data-score-view]').forEach((view) => view.classList.toggle('hidden-view', view.getAttribute('data-score-view') !== mode));
  }});
}});
document.querySelectorAll('table.sortable').forEach((tableEl) => {{
  const headers = tableEl.querySelectorAll('th.sortable-col');
  headers.forEach((header) => {{
    header.addEventListener('click', () => {{
      const colIndex = parseInt(header.getAttribute('data-sort-col'), 10);
      const current = header.getAttribute('data-sort-direction') || 'none';
      const direction = current === 'desc' ? 'asc' : 'desc';
      headers.forEach((other) => {{
        other.setAttribute('data-sort-direction', 'none');
        const indicator = other.querySelector('.sort-indicator');
        if (indicator) indicator.innerHTML = '&#x2195;';
      }});
      header.setAttribute('data-sort-direction', direction);
      const indicator = header.querySelector('.sort-indicator');
      if (indicator) indicator.innerHTML = direction === 'desc' ? '&#x25BC;' : '&#x25B2;';
      const tbody = tableEl.querySelector('tbody');
      const rows = Array.from(tbody.querySelectorAll('tr'));
      rows.sort((a, b) => {{
        const aCell = a.children[colIndex].querySelector('[data-sort]');
        const bCell = b.children[colIndex].querySelector('[data-sort]');
        const aRaw = aCell ? aCell.getAttribute('data-sort') : a.children[colIndex].innerText;
        const bRaw = bCell ? bCell.getAttribute('data-sort') : b.children[colIndex].innerText;
        const aNum = parseFloat(aRaw);
        const bNum = parseFloat(bRaw);
        const aValid = !Number.isNaN(aNum) && aRaw !== '';
        const bValid = !Number.isNaN(bNum) && bRaw !== '';
        if (!aValid && !bValid) return 0;
        if (!aValid) return 1;
        if (!bValid) return -1;
        return direction === 'desc' ? bNum - aNum : aNum - bNum;
      }});
      rows.forEach((row) => tbody.appendChild(row));
    }});
  }});
}});
</script>
</body></html>"""


def agent_payload(
    label: str,
    single_results: Path,
    multi_results: Path,
    dynamic_results: Path | None,
    single_master: Path,
    multi_master: Path,
) -> dict[str, Any]:
    single_rows = enrich_cases(test_cases(load_json(single_results)), load_master(single_master), "single_turn")
    multi_rows = enrich_cases(test_cases(load_json(multi_results)), load_master(multi_master), "fixed_multi_turn")
    static_rows = single_rows + multi_rows
    payload = {
        "agent": label,
        "static_rows": static_rows,
        "single_turn": summarize_static_rows(single_rows),
        "fixed_multi_turn": summarize_static_rows(multi_rows),
        "static_total": summarize_static_rows(static_rows),
        "dynamic": summarize_dynamic(load_json(dynamic_results)),
        "by_subagent": summarize_group(static_rows, lambda row: row["expected_topic"]),
        "by_taxonomy": summarize_group(static_rows, lambda row: f"{row['product']}|||{row['category']}|||{row['subcategory']}"),
        "by_tool_policy": summarize_group(static_rows, lambda row: row["tool_policy"]),
    }
    payload["score_modes"] = {mode: metric_for_mode(payload, "benchmark", mode) for mode in MODE_LABELS}
    return payload


def parse_agent_run(raw: str) -> tuple[str, Path, Path, Path | None]:
    parts = raw.split("::")
    if len(parts) not in {3, 4}:
        raise argparse.ArgumentTypeError(
            "--agent-run must be LABEL::single_results.json::multi_results.json[::dynamic_results.json]"
        )
    label, single, multi = parts[:3]
    dynamic = Path(parts[3]) if len(parts) == 4 and parts[3] else None
    return label, Path(single), Path(multi), dynamic


def payload_from_args(args: argparse.Namespace) -> dict[str, Any]:
    if args.agent_run:
        agents = [
            agent_payload(label, single, multi, dynamic, args.single_master, args.multi_master)
            for label, single, multi, dynamic in args.agent_run
        ]
        labels = {agent["agent"] for agent in agents}
        if not args.primary_agent_label:
            raise SystemExit("--primary-agent-label is required when --agent-run is used")
        if not args.baseline_agent_label:
            raise SystemExit("--baseline-agent-label is required when --agent-run is used")
        if args.primary_agent_label not in labels:
            raise SystemExit(f"--primary-agent-label {args.primary_agent_label!r} is not in --agent-run labels")
        if args.baseline_agent_label not in labels:
            raise SystemExit(f"--baseline-agent-label {args.baseline_agent_label!r} is not in --agent-run labels")
        return {"agents": agents, "primary_agent": args.primary_agent_label, "baseline_agent": args.baseline_agent_label}
    payload = agent_payload(args.agent_label, args.single_results, args.multi_results, args.dynamic_results, args.single_master, args.multi_master)
    payload["primary_agent"] = args.primary_agent_label or args.agent_label
    payload["baseline_agent"] = args.baseline_agent_label or args.agent_label
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--single-results", type=Path)
    parser.add_argument("--multi-results", type=Path)
    parser.add_argument("--dynamic-results", type=Path)
    parser.add_argument(
        "--agent-run",
        action="append",
        type=parse_agent_run,
        help="Repeatable comparison input: LABEL::single_results.json::multi_results.json[::dynamic_results.json]",
    )
    parser.add_argument("--single-master", type=Path, default=EVAL_ROOT / "single_turn_tests.csv")
    parser.add_argument("--multi-master", type=Path, default=EVAL_ROOT / "multi_turn_tests.csv")
    parser.add_argument("--agent-label", default="HelpIQ")
    parser.add_argument("--primary-agent-label", help="Agent used for detailed setup, latency, sub-agent, taxonomy, and dynamic breakdown sections.")
    parser.add_argument("--baseline-agent-label", help="Agent used as percentage-point delta anchor in multi-agent reports.")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if not args.agent_run and (not args.single_results or not args.multi_results):
        parser.error("--single-results and --multi-results are required unless --agent-run is provided")
    payload = payload_from_args(args)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "helpiq_evaluation_report.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    (args.output_dir / "helpiq_evaluation_report.html").write_text(html_report(payload))
    print(args.output_dir / "helpiq_evaluation_report.html")
    return 0


STYLES = """
:root{color-scheme:light;--text:#17202a;--border:#d9e2ec;--bg:#f7f9fb;--card:#fff;--warn:#8a5a00;--blue:#2454d6;--muted:#5f6b7a;--bad:#b42318;--good:#15803d;--inner:#fbfdff}
*{box-sizing:border-box}
html,body{overflow-x:hidden}
body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;color:var(--text);background:var(--bg);line-height:1.55}
main{max-width:1280px;margin:0 auto;padding:36px 28px 64px}
h1{font-size:32px;margin:0 0 10px}.subtitle{color:var(--muted);margin:0 0 18px;font-size:14px}
h2.section-heading{margin:30px 0 12px;padding-top:16px;border-top:1px solid var(--border);font-size:22px}h2.section-heading.first{margin-top:8px}h2:not(.section-heading){margin-top:32px;padding-top:16px;border-top:1px solid var(--border);font-size:20px}
.panel,.result-summary,.recommendation-panel,.versions-legend-wrap{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:16px 18px;box-shadow:0 1px 2px rgba(0,0,0,.04);margin:0 0 22px;min-width:0}
.panel-title,.label{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);font-weight:800;margin-bottom:10px;overflow-wrap:anywhere}
.versions-legend{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px}.version-card{display:flex;gap:12px;align-items:flex-start;background:var(--inner);border:1px solid var(--border);border-radius:12px;padding:12px 14px}.version-color{width:14px;height:14px;border-radius:3px;flex:0 0 14px;margin-top:4px}.version-info strong{display:block;margin-bottom:2px;font-size:14px}.version-meta{font-size:11px;color:var(--muted);margin-top:6px}
.metric-card-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:14px}.metric-card{background:var(--inner);border:1px solid var(--border);border-radius:12px;padding:14px 16px;display:flex;flex-direction:column;gap:10px;min-width:0;overflow:hidden}.metric-card-head{display:flex;align-items:center;justify-content:space-between;gap:8px}.metric-card-head .label{margin-bottom:0}.metric-headline{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}.metric-headline .value{font-size:28px;font-weight:760;line-height:1}
.bars{display:flex;flex-direction:column;gap:4px;margin-top:4px}.bar-row{display:grid;grid-template-columns:minmax(0,150px) minmax(80px,1fr) 60px 84px 50px;align-items:center;gap:8px;min-width:0}.bar-label{font-size:12px;font-weight:700;color:var(--text);min-width:0;overflow-wrap:anywhere;line-height:1.2}.bar-track{height:9px;background:#eef3f8;border-radius:999px;overflow:hidden}.bar-fill{height:100%;background:var(--blue);border-radius:999px}.bar-value,.bar-count,.bar-delta{font-size:11px;font-weight:700;text-align:right;color:var(--muted)}
.coverage-combined{display:grid;grid-template-columns:1fr 2fr;gap:14px}.coverage-card{background:var(--inner);border:1px solid var(--border);border-radius:12px;padding:12px 14px;min-width:0;overflow:hidden}.coverage-name{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);font-weight:800}.coverage-stats{display:grid;gap:8px;margin-top:8px}.coverage-top{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.coverage-stats span{font-size:11px;color:var(--muted)}.coverage-stats strong{display:block;color:var(--text);font-size:18px;line-height:1.1}.coverage-average{padding-top:8px;border-top:1px solid #eef3f8}.coverage-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.stat-value{font-size:22px;font-weight:760}.stat-label{font-size:11px;color:var(--muted)}
.hidden-view{display:none}
.floating-controls{position:fixed;right:18px;top:18px;z-index:30;display:flex;flex-direction:column;align-items:flex-end;gap:10px}.score-mode-floating{background:rgba(255,255,255,.96);border:1px solid var(--border);border-radius:14px;padding:10px 12px;box-shadow:0 6px 20px rgba(0,0,0,.12);max-width:360px}.score-mode-floating-title{display:flex;align-items:center;justify-content:flex-end;gap:6px;font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);font-weight:800;margin-bottom:8px}.score-mode-toggle{display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end}.score-mode-button{border:1px solid var(--border);background:var(--card);border-radius:999px;padding:7px 10px;font-size:12px;font-weight:800;cursor:pointer;color:var(--text);box-shadow:0 1px 2px rgba(0,0,0,.04)}.score-mode-button.active{background:var(--blue);border-color:var(--blue);color:#fff}
.score-mode-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px;margin:12px 0 16px}.score-mode-card{background:var(--inner);border:1px solid var(--border);border-radius:12px;padding:14px 16px;min-width:0;overflow:hidden}.score-mode-card:first-child{border-left:5px solid var(--blue)}.score-mode-value{font-size:30px;font-weight:800;line-height:1.1;margin:8px 0}.score-mode-card p{font-size:12px;margin:8px 0 0;color:var(--text)}
.recommendation-grid{display:grid;grid-template-columns:1fr 1.5fr;gap:14px}.recommendation-card{background:var(--inner);border:1px solid var(--border);border-radius:12px;padding:14px 16px;min-width:0;overflow:hidden}.recommendation-card.note-card{border-left:5px solid var(--good)}.recommendation-card .verdict{font-size:22px;font-weight:800;color:var(--good);margin:0}.recommendation-card p{margin:0 0 8px}.hint{font-size:12px;color:var(--muted)}
.table-wrap{width:100%;max-width:100%;overflow-x:auto;overflow-y:hidden;margin:14px 0 24px;-webkit-overflow-scrolling:touch}table{width:100%;min-width:1040px;border-collapse:collapse;background:var(--card);border:1px solid var(--border);table-layout:auto}th,td{padding:9px 11px;border-bottom:1px solid var(--border);vertical-align:top;font-size:12px;overflow-wrap:anywhere}th{background:#eef3f8;text-align:left;white-space:nowrap}code{background:#eef3f8;padding:1px 5px;border-radius:3px;font-size:12px;white-space:normal;overflow-wrap:anywhere}.subagent-benchmark{font-weight:700;color:var(--text)}.subagent-delta{font-size:11px;font-weight:700;color:var(--muted);margin-top:2px}
th.sortable-col{cursor:pointer;user-select:none}th.sortable-col:hover{background:#dde6f1}th.sortable-col .sort-indicator{font-size:10px;color:var(--muted);margin-left:4px}th.sortable-col[data-sort-direction="asc"] .sort-indicator,th.sortable-col[data-sort-direction="desc"] .sort-indicator{color:var(--blue)}
.detail-toggle{padding:0;margin:8px 0 0}.detail-toggle summary{cursor:pointer;list-style:none;padding:10px 0 0;font-weight:800;color:var(--blue)}.detail-toggle summary::-webkit-details-marker{display:none}.detail-toggle .hide-label{display:none}.detail-toggle[open] .show-label{display:none}.detail-toggle[open] .hide-label{display:inline}
ul{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:14px 22px 14px 34px}ul li{margin:6px 0;font-size:13px;line-height:1.6}
.info-tip{position:relative;display:inline-flex;align-items:center;justify-content:center;min-width:16px;height:16px;border-radius:999px;border:1px solid #d9e2ec;color:#2454d6;background:#eef3f8;font-size:10px;font-weight:800;cursor:help;text-transform:none;letter-spacing:0}.info-tip:hover::after,.info-tip:focus::after{content:attr(data-tip);position:absolute;right:0;top:22px;z-index:60;width:min(280px,70vw);background:#17202a;color:#fff;border-radius:8px;padding:8px 10px;font-size:11px;font-weight:600;line-height:1.4;text-transform:none;letter-spacing:0;box-shadow:0 10px 28px rgba(0,0,0,.22);white-space:normal}
.guide-toggle{border:0;border-radius:999px;background:var(--blue);color:#fff;font-weight:800;padding:9px 14px;box-shadow:0 6px 20px rgba(0,0,0,.18);cursor:pointer;font-size:13px}.guide-panel{position:fixed;right:0;top:0;z-index:29;width:min(520px,92vw);height:100vh;background:var(--card);border-left:1px solid var(--border);box-shadow:-12px 0 30px rgba(0,0,0,.16);transform:translateX(100%);transition:transform .25s ease;overflow-y:auto;padding:18px 24px 48px}.guide-open .guide-panel{transform:translateX(0)}.guide-close{position:sticky;top:0;float:right;border:1px solid var(--border);background:var(--card);border-radius:999px;padding:6px 12px;font-weight:800;cursor:pointer;font-size:12px}.guide-content{clear:both;padding-top:8px}.guide-content h2{display:block;border-top:0;margin:14px 0 10px;padding-top:0;font-size:22px}.guide-content h3{border-top:1px solid var(--border);margin:22px 0 8px;padding-top:14px;font-size:16px}.guide-content p,.guide-content li{font-size:13px;line-height:1.55}.guide-content ul{background:transparent;border:0;border-radius:0;padding:0 0 0 20px;margin:6px 0 10px}
@media(max-width:760px){main{padding:28px 16px 56px}.metric-card-grid{grid-template-columns:minmax(0,1fr)}.bar-row{grid-template-columns:minmax(0,118px) minmax(60px,1fr) 52px 70px 42px;gap:6px}.coverage-combined{grid-template-columns:1fr}.coverage-grid{grid-template-columns:1fr}.recommendation-grid{grid-template-columns:1fr}}
"""


if __name__ == "__main__":
    raise SystemExit(main())
