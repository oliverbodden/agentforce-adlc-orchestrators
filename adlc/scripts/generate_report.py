#!/usr/bin/env python3
"""Generate a topic-agnostic regression report comparing baseline vs new eval CSVs.

Usage:
    python3 generate_report.py --prev <baseline.csv> --new <new.csv> --output <report.html> --title "Report Title"

Metrics are discovered from the data, not hardcoded. Works for any topic.
"""
import argparse
import csv
import html as html_mod
import re
import statistics
import sys
from collections import Counter, defaultdict
from difflib import SequenceMatcher


def load_csv(path):
    rows = list(csv.DictReader(open(path, encoding='utf-8')))
    result = []
    for row in rows:
        mapped = {}
        for c, v in row.items():
            cl = c.lower().strip()
            if cl == 'utterance':
                mapped['utterance'] = v or ''
            elif cl in ('actual outcome', 'agent response'):
                mapped['response'] = html_mod.unescape(v or '')
            elif 'latency' in cl:
                try:
                    mapped['latency_ms'] = float(v) if v else None
                except (ValueError, TypeError):
                    mapped['latency_ms'] = None
            elif cl == 'actual action':
                mapped['actions'] = v or ''
        result.append(mapped)
    return result


def extract_user_response(text):
    text = html_mod.unescape(text)
    parts = re.split(r'\*\*My Response:\*\*', text, flags=re.IGNORECASE)
    if len(parts) > 1:
        return parts[-1].strip()
    return text.strip()


def get_response_features(resp):
    """Extract topic-agnostic features from a response."""
    features = {}
    features['length'] = len(resp)
    features['has_link'] = bool(re.search(r'\[.*?\]\(http', resp))
    features['has_numbered_list'] = bool(re.search(r'^\s*\d+\.', resp, re.M))
    features['has_bullets'] = bool(re.search(r'^\s*[-*]\s', resp, re.M))
    features['has_bold'] = '**' in resp
    features['has_did_this_help'] = bool(re.search(r'did this help', resp, re.I))
    features['has_representative'] = bool(re.search(r'representative|connect you', resp, re.I))
    features['has_invoice'] = bool(re.search(r'USI|INV|invoice\s*#', resp, re.I))
    features['has_dollar'] = bool(re.search(r'\$[\d,]+', resp))
    features['has_knowledge'] = bool(re.search(r'article|knowledge|learn more|help center', resp, re.I))
    features['has_url'] = bool(re.search(r'https?://', resp))
    features['has_qa_url'] = bool(re.search(r'qa-|staging', resp, re.I))
    return features


def check_redundancy(text):
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
    trigrams = re.findall(r'\b\w+\s+\w+\s+\w+\b', text.lower())
    trigram_counts = Counter(trigrams)
    has_repeated = any(c >= 2 for c in trigram_counts.values())
    has_similar = False
    for i in range(len(sentences)):
        for j in range(i + 1, len(sentences)):
            if SequenceMatcher(None, sentences[i], sentences[j]).ratio() > 0.6:
                has_similar = True
                break
    return has_repeated, has_similar


def check_robotic_echo(utterance, response, n=4):
    words = utterance.lower().split()
    if len(words) < n:
        return False
    ngrams = [' '.join(words[i:i+n]) for i in range(len(words) - n + 1)]
    skip = {'did this help', 'here s what'}
    for ng in ngrams:
        if ng in skip:
            continue
        if ng in response.lower():
            return True
    return False


def percentile(data, p):
    s = sorted(data)
    k = (len(s) - 1) * p / 100
    f = int(k)
    c = f + 1
    if c >= len(s):
        return s[-1]
    return s[f] + (k - f) * (s[c] - s[f])


def analyze(rows, label):
    """Run topic-agnostic analysis on a dataset."""
    results = {}

    # Overview
    utts = set(r['utterance'] for r in rows)
    results['total_rows'] = len(rows)
    results['unique_utterances'] = len(utts)

    latencies = [r['latency_ms'] / 1000 for r in rows if r.get('latency_ms')]
    if latencies:
        results['latency_median'] = round(statistics.median(latencies), 2)
        results['latency_mean'] = round(statistics.mean(latencies), 2)
        results['latency_p90'] = round(percentile(latencies, 90), 2)

    # Response features (topic-agnostic)
    user_responses = [extract_user_response(r.get('response', '')) for r in rows]
    n = len(user_responses)

    feature_rates = defaultdict(int)
    for resp in user_responses:
        features = get_response_features(resp)
        for k, v in features.items():
            if isinstance(v, bool) and v:
                feature_rates[k] += 1

    results['features'] = {k: round(v / n * 100, 1) for k, v in feature_rates.items()}

    # Length stats
    lengths = [len(r) for r in user_responses]
    results['length_median'] = round(statistics.median(lengths))
    results['length_mean'] = round(statistics.mean(lengths))

    # Redundancy
    any_r = rep = sim = 0
    for r in user_responses:
        rp, sm = check_redundancy(r)
        if rp: rep += 1
        if sm: sim += 1
        if rp or sm: any_r += 1
    results['redundancy'] = round(any_r / n * 100, 1)
    results['redundancy_repeated'] = round(rep / n * 100, 1)
    results['redundancy_similar'] = round(sim / n * 100, 1)

    # Robotic echo
    echo4 = sum(1 for r, row in zip(user_responses, rows) if check_robotic_echo(row['utterance'], r, 4))
    echo6 = sum(1 for r, row in zip(user_responses, rows) if check_robotic_echo(row['utterance'], r, 6))
    results['echo_4word'] = round(echo4 / n * 100, 1)
    results['echo_6word'] = round(echo6 / n * 100, 1)

    # Consistency (if multiple runs per utterance)
    groups = defaultdict(list)
    for r in rows:
        groups[r['utterance']].append(extract_user_response(r.get('response', '')))
    multi = {u: resps for u, resps in groups.items() if len(resps) >= 2}

    if multi:
        all_sims = []
        gt90 = 0
        for resps in multi.values():
            pairs = []
            for i in range(len(resps)):
                for j in range(i + 1, len(resps)):
                    pairs.append(SequenceMatcher(None, resps[i], resps[j]).ratio())
            all_sims.extend(pairs)
            if pairs and min(pairs) > 0.9:
                gt90 += 1
        results['consistency_sim_mean'] = round(statistics.mean(all_sims), 3) if all_sims else None
        results['consistency_gt90'] = round(gt90 / len(multi) * 100, 1) if multi else None
    else:
        results['consistency_sim_mean'] = None
        results['consistency_gt90'] = None

    return results


def format_delta(prev_val, new_val, higher_is_better=True):
    if prev_val is None or new_val is None:
        return "N/A"
    delta = new_val - prev_val
    if abs(delta) < 0.1:
        return f"{delta:+.1f} (flat)"
    if (delta > 0) == higher_is_better:
        return f"<span style='color:#22c55e;font-weight:600'>{delta:+.1f}</span>"
    else:
        return f"<span style='color:#ef4444;font-weight:600'>{delta:+.1f}</span>"


def generate_html(prev_results, new_results, title):
    rows = []

    def add(label, prev_key, higher_is_better=True, suffix=''):
        pv = prev_results.get(prev_key)
        nv = new_results.get(prev_key)
        pv_str = f"{pv}{suffix}" if pv is not None else "N/A"
        nv_str = f"{nv}{suffix}" if nv is not None else "N/A"
        delta = format_delta(pv, nv, higher_is_better)
        rows.append(f"<tr><td>{label}</td><td>{pv_str}</td><td><strong>{nv_str}</strong></td><td>{delta}</td></tr>")

    # Overview
    rows.append("<tr style='background:#f3f4f6'><td colspan='4'><strong>Overview</strong></td></tr>")
    add("Total rows", "total_rows", True)
    add("Unique utterances", "unique_utterances", True)
    add("Latency median", "latency_median", False, "s")
    add("Length median", "length_median", False, " chars")

    # Features
    rows.append("<tr style='background:#f3f4f6'><td colspan='4'><strong>Response Features</strong></td></tr>")
    all_features = set(list(prev_results.get('features', {}).keys()) + list(new_results.get('features', {}).keys()))
    for feat in sorted(all_features):
        pv = prev_results.get('features', {}).get(feat)
        nv = new_results.get('features', {}).get(feat)
        label = feat.replace('has_', '').replace('_', ' ').title()
        pv_str = f"{pv}%" if pv is not None else "N/A"
        nv_str = f"{nv}%" if nv is not None else "N/A"
        # Most features: higher is better, except qa_url and representative
        hib = feat not in ('has_qa_url', 'has_representative')
        delta = format_delta(pv, nv, hib)
        rows.append(f"<tr><td>{label}</td><td>{pv_str}</td><td><strong>{nv_str}</strong></td><td>{delta}</td></tr>")

    # Quality
    rows.append("<tr style='background:#f3f4f6'><td colspan='4'><strong>Quality</strong></td></tr>")
    add("Redundancy", "redundancy", False, "%")
    add("Robotic echo (4+ word)", "echo_4word", False, "%")
    add("Robotic echo (6+ word)", "echo_6word", False, "%")

    # Consistency
    rows.append("<tr style='background:#f3f4f6'><td colspan='4'><strong>Consistency</strong></td></tr>")
    add("Pairwise similarity mean", "consistency_sim_mean", True)
    add("All pairs >90% similar", "consistency_gt90", True, "%")

    table_rows = "\n".join(rows)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
       background: #f9fafb; color: #1f2937; line-height: 1.6; padding: 2rem;
       max-width: 1000px; margin: 0 auto; }}
h1 {{ font-size: 1.5rem; border-bottom: 2px solid #e5e7eb; padding-bottom: 0.5rem; }}
table {{ width: 100%; border-collapse: collapse; font-size: 0.875rem; margin: 1rem 0; }}
th {{ text-align: left; padding: 0.5rem; background: #1f2937; color: white; }}
td {{ padding: 0.45rem 0.75rem; border-bottom: 1px solid #e5e7eb; }}
tr:hover td {{ background: #f9fafb; }}
</style>
</head>
<body>
<h1>{title}</h1>
<p style="color:#6b7280;">Topic-agnostic regression report. Metrics discovered from data.</p>
<table>
<tr><th>Metric</th><th>Baseline</th><th>New</th><th>Delta</th></tr>
{table_rows}
</table>
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser(description="Topic-agnostic regression report")
    parser.add_argument("--prev", required=True, help="Baseline CSV")
    parser.add_argument("--new", required=True, help="New results CSV")
    parser.add_argument("--output", required=True, help="Output HTML path")
    parser.add_argument("--title", default="Eval Regression Report")
    args = parser.parse_args()

    prev_rows = load_csv(args.prev)
    new_rows = load_csv(args.new)

    print(f"Baseline: {len(prev_rows)} rows | New: {len(new_rows)} rows")

    prev_results = analyze(prev_rows, "Baseline")
    new_results = analyze(new_rows, "New")

    # Print text summary
    print(f"\n{'Metric':<35} {'Baseline':>10} {'New':>10} {'Delta':>10}")
    print("-" * 70)
    for key in ['total_rows', 'unique_utterances', 'latency_median', 'length_median',
                 'redundancy', 'echo_4word']:
        pv = prev_results.get(key, 'N/A')
        nv = new_results.get(key, 'N/A')
        delta = ''
        if isinstance(pv, (int, float)) and isinstance(nv, (int, float)):
            delta = f"{nv - pv:+.1f}"
        print(f"{key:<35} {str(pv):>10} {str(nv):>10} {delta:>10}")

    print(f"\nResponse features:")
    all_feats = set(list(prev_results.get('features', {}).keys()) + list(new_results.get('features', {}).keys()))
    for f in sorted(all_feats):
        pv = prev_results.get('features', {}).get(f, 'N/A')
        nv = new_results.get('features', {}).get(f, 'N/A')
        delta = ''
        if isinstance(pv, (int, float)) and isinstance(nv, (int, float)):
            delta = f"{nv - pv:+.1f}"
        label = f.replace('has_', '')
        print(f"  {label:<30} {str(pv):>8}% {str(nv):>8}% {delta:>10}")

    # Generate HTML
    html = generate_html(prev_results, new_results, args.title)
    with open(args.output, 'w') as f:
        f.write(html)
    print(f"\nReport: {args.output}")


if __name__ == "__main__":
    main()
