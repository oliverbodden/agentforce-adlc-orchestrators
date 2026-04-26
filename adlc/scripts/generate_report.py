#!/usr/bin/env python3
"""Generate a topic-agnostic regression report comparing baseline vs new eval CSVs.

Usage:
    python3 generate_report.py --prev <baseline.csv> --new <new.csv> --output <report.html> --title "Report Title"
    python3 generate_report.py --prev <baseline.csv> --new <new.csv> --output <report.html> --json-output <report.json>
    python3 generate_report.py --prev <baseline.csv> --new <new.csv> --output <report.html> --full-appendix

Produces:
  - HTML report with scorecard, metric tables, and response comparison appendix
  - Optional JSON sidecar with all computed metrics for programmatic consumption
"""
import argparse
import csv
import html as html_mod
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from difflib import SequenceMatcher


# ---------------------------------------------------------------------------
# CSV loading
# ---------------------------------------------------------------------------

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
            elif cl == 'actual topic':
                mapped['topic'] = v or ''
        result.append(mapped)
    return result


def extract_user_response(text):
    text = html_mod.unescape(text)
    parts = re.split(r'\*\*My Response:\*\*', text, flags=re.IGNORECASE)
    if len(parts) > 1:
        return parts[-1].strip()
    return text.strip()


# ---------------------------------------------------------------------------
# Strategy classification
# ---------------------------------------------------------------------------

STRATEGY_PATTERNS = [
    ('EXPLAIN', [
        r"here.s what i found",
        r"here.s what i see",
        r"based on (?:your|the) (?:account|information)",
        r"i (?:can see|see) that",
        r"looking at your",
        r"according to",
        r"let me (?:explain|walk you through|break)",
        r"i (?:looked into|checked|reviewed|pulled up)",
        r"(?:to|you can|you.ll want to|you.ll need to).*(?:go to|navigate|click|visit|head to|log in)",
        r"did this help",
        r"(?:here|this) is (?:how|what|the)",
        r"the (?:answer|reason|explanation|solution|issue|status) is",
        r"great question",
    ]),
    ('ESCALATE', [
        r"connect you with",
        r"transfer you",
        r"representative",
        r"(?:create|open|file|submit).*(?:case|ticket|request)",
        r"escalat",
        r"human agent",
        r"support team",
    ]),
    ('CLARIFY', [
        r"could you (?:clarify|provide|share|tell me)",
        r"can you (?:clarify|provide|share|tell me)",
        r"i need (?:a bit )?more (?:information|details|context)",
        r"which (?:one|account|invoice|job)",
        r"do you mean",
        r"to help you.*i.ll need",
    ]),
    ('POST_RESOLUTION', [
        r"(?:is there|was there) anything else",
        r"glad i could help",
        r"happy i could (?:help|assist)",
        r"(?:resolve|address|answer).*(?:question|concern|issue)",
        r"have a (?:great|wonderful|good) day",
    ]),
]


def classify_strategy(response):
    resp_lower = response.lower()
    for strategy, patterns in STRATEGY_PATTERNS:
        for pat in patterns:
            if re.search(pat, resp_lower):
                return strategy
    return 'OTHER'


# ---------------------------------------------------------------------------
# Turn classification (single vs follow-up)
# ---------------------------------------------------------------------------

FOLLOWUP_PATTERNS = re.compile(
    r'^(yes|no|ok|okay|sure|nope|yep|yeah|nah|correct|right|exactly|'
    r'that.s it|i.m good|none|not really|understood|got it|thanks|thank you|'
    r'no thanks|no thank you|actually|hmm|mmmm)[\s.,!?]*$', re.I
)


def is_followup(utterance):
    return bool(FOLLOWUP_PATTERNS.match(utterance.strip())) or len(utterance.split()) <= 4


# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------

def get_response_features(resp):
    features = {}
    features['length'] = len(resp)
    features['has_link'] = bool(re.search(r'\[.*?\]\(http', resp))
    features['has_numbered_list'] = bool(re.search(r'^\s*\d+\.', resp, re.M))
    features['has_bullets'] = bool(re.search(r'^\s*[-*]\s', resp, re.M))
    features['has_bold'] = '**' in resp
    features['has_section_labels'] = bool(re.search(r'\*\*[A-Z][^*]+:\*\*', resp))
    features['has_markdown_headers'] = bool(re.search(r'^#{1,3}\s', resp, re.M))
    features['has_did_this_help'] = bool(re.search(r'did this help', resp, re.I))
    features['has_representative'] = bool(re.search(r'representative|connect you', resp, re.I))
    features['has_invoice'] = bool(re.search(r'USI|INV|invoice\s*#', resp, re.I))
    features['has_dollar'] = bool(re.search(r'\$[\d,]+', resp))
    features['has_knowledge'] = bool(re.search(r'article|knowledge|learn more|help center', resp, re.I))
    features['has_url'] = bool(re.search(r'https?://', resp))
    features['has_qa_url'] = bool(re.search(r'qa-|staging', resp, re.I))
    features['has_happy_to_help'] = bool(re.search(r'happy to help', resp[:100], re.I))
    features['has_log_leak'] = bool(re.search(
        r'\bStore:|ActionPlan|reasoning_trace|<internal>|SYSTEM:', resp))
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


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def analyze(rows, label):
    results = {}
    n = len(rows)
    if n == 0:
        return results

    utts = set(r['utterance'] for r in rows)
    results['total_rows'] = n
    results['unique_utterances'] = len(utts)

    # Classify turns
    single = [r for r in rows if not is_followup(r['utterance'])]
    followup = [r for r in rows if is_followup(r['utterance'])]
    results['single_turn'] = len(single)
    results['follow_up'] = len(followup)

    # Latency
    latencies = [r['latency_ms'] / 1000 for r in rows if r.get('latency_ms')]
    if latencies:
        results['latency_median'] = round(statistics.median(latencies), 2)
        results['latency_mean'] = round(statistics.mean(latencies), 2)
        results['latency_p90'] = round(percentile(latencies, 90), 2)

    user_responses = [extract_user_response(r.get('response', '')) for r in rows]

    # Strategy distribution
    strategies = [classify_strategy(r) for r in user_responses]
    strat_counts = Counter(strategies)
    results['strategy'] = {s: round(c / n * 100, 1) for s, c in strat_counts.items()}

    # Strategy consistency per utterance (across runs)
    utt_strategies = defaultdict(list)
    for row, strat in zip(rows, strategies):
        utt_strategies[row['utterance']].append(strat)
    multi_strat = {u: s for u, s in utt_strategies.items() if len(s) >= 2}
    if multi_strat:
        all_same = sum(1 for s in multi_strat.values() if len(set(s)) == 1)
        two_diff = sum(1 for s in multi_strat.values() if len(set(s)) == 2)
        three_plus = sum(1 for s in multi_strat.values() if len(set(s)) >= 3)
        total_m = len(multi_strat)
        results['strat_all_same'] = round(all_same / total_m * 100, 1)
        results['strat_2_diff'] = round(two_diff / total_m * 100, 1)
        results['strat_3_plus'] = round(three_plus / total_m * 100, 1)
        modal_matches = 0
        modal_total = 0
        for s_list in multi_strat.values():
            mode = Counter(s_list).most_common(1)[0][0]
            modal_matches += sum(1 for x in s_list if x == mode)
            modal_total += len(s_list)
        results['strat_modal_match'] = round(modal_matches / modal_total * 100, 1)

    # Tool calling
    actions_list = [r.get('actions', '') for r in rows]
    has_any_action = [bool(a.strip()) for a in actions_list]
    if any(has_any_action):
        results['tool_any'] = round(sum(has_any_action) / n * 100, 1)
        tool_counts = defaultdict(int)
        for a in actions_list:
            if a.strip():
                for part in re.split(r'[,;→\n]+', a):
                    tool_name = re.sub(r'_[A-Za-z0-9]{15,18}$', '', part.strip())
                    if tool_name:
                        tool_counts[tool_name] += 1
        results['tool_breakdown'] = {t: round(c / n * 100, 1) for t, c in tool_counts.items()}

        single_actions = [r.get('actions', '') for r in single]
        follow_actions = [r.get('actions', '') for r in followup]
        if single_actions:
            results['tool_single'] = round(
                sum(1 for a in single_actions if a.strip()) / len(single_actions) * 100, 1)
        if follow_actions:
            results['tool_followup'] = round(
                sum(1 for a in follow_actions if a.strip()) / len(follow_actions) * 100, 1)

    # Response features
    feature_rates = defaultdict(int)
    for resp in user_responses:
        features = get_response_features(resp)
        for k, v in features.items():
            if isinstance(v, bool) and v:
                feature_rates[k] += 1
    results['features'] = {k: round(v / n * 100, 1) for k, v in feature_rates.items()}

    # Opening behavior — split by turn type
    single_responses = [extract_user_response(r.get('response', '')) for r in single]
    followup_responses = [extract_user_response(r.get('response', '')) for r in followup]

    if single_responses:
        hth_single = sum(1 for r in single_responses if re.search(r'happy to help', r[:100], re.I))
        results['opening_happy_single'] = round(hth_single / len(single_responses) * 100, 1)
    if followup_responses:
        hth_follow = sum(1 for r in followup_responses if re.search(r'happy to help', r[:100], re.I))
        direct_follow = sum(1 for r in followup_responses
                           if not re.search(r'^(sure|of course|absolutely|great|happy to)', r[:60], re.I))
        results['opening_happy_follow'] = round(hth_follow / len(followup_responses) * 100, 1)
        results['opening_direct_follow'] = round(direct_follow / len(followup_responses) * 100, 1)

    # Length stats + buckets
    lengths = [len(r) for r in user_responses]
    word_counts = [len(r.split()) for r in user_responses]
    results['length_median'] = round(statistics.median(lengths))
    results['length_mean'] = round(statistics.mean(lengths))
    results['words_median'] = round(statistics.median(word_counts))
    results['words_mean'] = round(statistics.mean(word_counts))
    results['len_lte_500'] = round(sum(1 for l in lengths if l <= 500) / n * 100, 1)
    results['len_500_1000'] = round(sum(1 for l in lengths if 500 < l <= 1000) / n * 100, 1)
    results['len_gt_1000'] = round(sum(1 for l in lengths if l > 1000) / n * 100, 1)
    results['len_gt_1500'] = round(sum(1 for l in lengths if l > 1500) / n * 100, 1)

    # Safety
    log_leaks = sum(1 for r in user_responses if get_response_features(r)['has_log_leak'])
    results['log_leak'] = round(log_leaks / n * 100, 1)

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

    # Consistency (cross-run pairwise similarity)
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


# ---------------------------------------------------------------------------
# Scorecard
# ---------------------------------------------------------------------------

def build_scorecard(prev, new):
    """Compare all numeric metrics, return wins/regressions/ties and per-metric details."""
    LOWER_IS_BETTER = {
        'length_median', 'length_mean', 'words_median', 'words_mean',
        'latency_median', 'latency_mean', 'latency_p90',
        'redundancy', 'redundancy_repeated', 'redundancy_similar',
        'echo_4word', 'echo_6word', 'log_leak',
        'len_gt_1000', 'len_gt_1500',
        'strat_3_plus',
    }
    IGNORE = {'total_rows', 'unique_utterances', 'single_turn', 'follow_up'}

    metrics = []

    def compare(label, pv, nv, lower_better=False):
        if pv is None or nv is None:
            return
        delta = nv - pv
        if abs(delta) < 0.05:
            winner = 'tie'
        elif (delta < 0) == lower_better:
            winner = 'new'
        else:
            winner = 'prev'
        metrics.append({'label': label, 'prev': pv, 'new': nv,
                        'delta': round(delta, 1), 'winner': winner})

    # Flat metrics
    all_keys = set(list(prev.keys()) + list(new.keys()))
    for k in sorted(all_keys):
        if k in IGNORE or k in ('features', 'strategy'):
            continue
        pv, nv = prev.get(k), new.get(k)
        if not isinstance(pv, (int, float)) or not isinstance(nv, (int, float)):
            continue
        label = k.replace('_', ' ').title()
        compare(label, pv, nv, k in LOWER_IS_BETTER)

    # Strategy metrics
    all_strats = set(list(prev.get('strategy', {}).keys()) + list(new.get('strategy', {}).keys()))
    for s in sorted(all_strats):
        pv = prev.get('strategy', {}).get(s, 0)
        nv = new.get('strategy', {}).get(s, 0)
        lb = s == 'OTHER'
        compare(f"Strategy: {s}", pv, nv, lb)

    # Tool metrics
    for key, label, lb in [('tool_any', 'Any tool called', False),
                           ('tool_single', 'Tool on single-turn', False),
                           ('tool_followup', 'Tool on follow-up', True)]:
        pv, nv = prev.get(key), new.get(key)
        if pv is not None or nv is not None:
            compare(label, pv, nv, lb)
    all_tools = set(list(prev.get('tool_breakdown', {}).keys()) +
                    list(new.get('tool_breakdown', {}).keys()))
    for t in sorted(all_tools):
        pv = prev.get('tool_breakdown', {}).get(t, 0)
        nv = new.get('tool_breakdown', {}).get(t, 0)
        compare(f"Tool: {t}", pv, nv, False)

    # Feature metrics
    all_feats = set(list(prev.get('features', {}).keys()) + list(new.get('features', {}).keys()))
    for f in sorted(all_feats):
        pv = prev.get('features', {}).get(f, 0)
        nv = new.get('features', {}).get(f, 0)
        lb = f in ('has_qa_url', 'has_representative', 'has_log_leak',
                    'has_bullets', 'has_numbered_list', 'has_section_labels', 'has_markdown_headers')
        label = f.replace('has_', '').replace('_', ' ').title()
        compare(label, pv, nv, lb)

    wins = sum(1 for m in metrics if m['winner'] == 'new')
    regressions = sum(1 for m in metrics if m['winner'] == 'prev')
    ties = sum(1 for m in metrics if m['winner'] == 'tie')

    return {'wins': wins, 'regressions': regressions, 'ties': ties, 'details': metrics}


# ---------------------------------------------------------------------------
# Response comparison appendix
# ---------------------------------------------------------------------------

def build_appendix(prev_rows, new_rows, prev_results, new_results, full=False):
    """Build per-utterance comparison. Returns list of dicts."""
    prev_by_utt = defaultdict(list)
    for r in prev_rows:
        prev_by_utt[r['utterance']].append(r)
    new_by_utt = defaultdict(list)
    for r in new_rows:
        new_by_utt[r['utterance']].append(r)

    all_utts = sorted(set(list(prev_by_utt.keys()) + list(new_by_utt.keys())))
    comparisons = []

    for utt in all_utts:
        prev_resps = [extract_user_response(r.get('response', '')) for r in prev_by_utt.get(utt, [])]
        new_resps = [extract_user_response(r.get('response', '')) for r in new_by_utt.get(utt, [])]

        prev_rep = prev_resps[0] if prev_resps else ''
        new_rep = new_resps[0] if new_resps else ''

        prev_strat = classify_strategy(prev_rep) if prev_rep else 'N/A'
        new_strat = classify_strategy(new_rep) if new_rep else 'N/A'

        prev_len = len(prev_rep)
        new_len = len(new_rep)
        len_delta = new_len - prev_len
        len_delta_pct = (len_delta / prev_len * 100) if prev_len > 0 else 0

        flags = []
        if prev_strat != new_strat:
            flags.append(f"strategy: {prev_strat}\u2192{new_strat}")
        if abs(len_delta_pct) > 50:
            flags.append(f"length: {len_delta_pct:+.0f}%")
        if get_response_features(new_rep).get('has_log_leak'):
            flags.append("log leak")

        comparisons.append({
            'utterance': utt,
            'prev_response': prev_rep,
            'new_response': new_rep,
            'prev_strategy': prev_strat,
            'new_strategy': new_strat,
            'prev_len': prev_len,
            'new_len': new_len,
            'len_delta': len_delta,
            'len_delta_pct': round(len_delta_pct, 1),
            'flags': flags,
            'is_interesting': len(flags) > 0,
        })

    if full:
        return comparisons
    return [c for c in comparisons if c['is_interesting']]


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------

def format_delta(prev_val, new_val, higher_is_better=True):
    if prev_val is None or new_val is None:
        return "N/A"
    delta = new_val - prev_val
    if abs(delta) < 0.05:
        return f"{delta:+.1f} ~"
    if (delta > 0) == higher_is_better:
        return f"<span style='color:#22c55e;font-weight:600'>{delta:+.1f}</span>"
    else:
        return f"<span style='color:#ef4444;font-weight:600'>{delta:+.1f}</span>"


def _esc(text):
    return html_mod.escape(text)


def generate_html(prev_results, new_results, scorecard, appendix, title, total_utterances=0):
    parts = []

    # --- Scorecard summary ---
    sc = scorecard
    parts.append(f"""
    <div style="display:flex;gap:1.5rem;margin:1.5rem 0">
      <div style="flex:1;background:#ecfdf5;border:1px solid #86efac;border-radius:8px;padding:1rem;text-align:center">
        <div style="font-size:2rem;font-weight:700;color:#16a34a">{sc['wins']}</div>
        <div style="color:#166534;font-size:0.85rem">Wins</div>
      </div>
      <div style="flex:1;background:#fef2f2;border:1px solid #fca5a5;border-radius:8px;padding:1rem;text-align:center">
        <div style="font-size:2rem;font-weight:700;color:#dc2626">{sc['regressions']}</div>
        <div style="color:#991b1b;font-size:0.85rem">Regressions</div>
      </div>
      <div style="flex:1;background:#f3f4f6;border:1px solid #d1d5db;border-radius:8px;padding:1rem;text-align:center">
        <div style="font-size:2rem;font-weight:700;color:#6b7280">{sc['ties']}</div>
        <div style="color:#374151;font-size:0.85rem">Ties</div>
      </div>
    </div>""")

    # --- Overview ---
    parts.append("<h2>Overview</h2>")
    parts.append("""<table><tr><th>Metric</th><th>Baseline</th><th>New</th></tr>""")
    for key, label in [('total_rows', 'Total rows'), ('unique_utterances', 'Unique utterances'),
                       ('single_turn', 'Single-turn'), ('follow_up', 'Follow-up')]:
        pv = prev_results.get(key, 'N/A')
        nv = new_results.get(key, 'N/A')
        parts.append(f"<tr><td>{label}</td><td>{pv}</td><td>{nv}</td></tr>")
    parts.append("</table>")

    # --- Metric table helper ---
    def metric_table(section_title, rows_data):
        parts.append(f"<h2>{section_title}</h2>")
        parts.append("<table><tr><th>Metric</th><th>Baseline</th><th>New</th><th>Delta</th></tr>")
        for label, pv, nv, hib, suffix in rows_data:
            pv_str = f"{pv}{suffix}" if pv is not None else "N/A"
            nv_str = f"{nv}{suffix}" if nv is not None else "N/A"
            d = format_delta(pv, nv, hib)
            parts.append(f"<tr><td>{label}</td><td>{pv_str}</td><td><strong>{nv_str}</strong></td><td>{d}</td></tr>")
        parts.append("</table>")

    # --- Safety ---
    metric_table("Safety", [
        ("Log leak in response", prev_results.get('log_leak'), new_results.get('log_leak'), False, "%"),
    ])

    # --- Tool Calling ---
    if prev_results.get('tool_any') is not None or new_results.get('tool_any') is not None:
        tool_rows = [
            ("Any tool called", prev_results.get('tool_any'), new_results.get('tool_any'), True, "%"),
            ("Tool on single-turn", prev_results.get('tool_single'), new_results.get('tool_single'), True, "%"),
            ("Tool on follow-up", prev_results.get('tool_followup'), new_results.get('tool_followup'), False, "%"),
        ]
        all_tools = sorted(set(
            list(prev_results.get('tool_breakdown', {}).keys()) +
            list(new_results.get('tool_breakdown', {}).keys())
        ))
        for t in all_tools:
            pv = prev_results.get('tool_breakdown', {}).get(t, 0)
            nv = new_results.get('tool_breakdown', {}).get(t, 0)
            tool_rows.append((f"Tool: {t}", pv, nv, True, "%"))
        metric_table("Tool Calling", tool_rows)

    # --- Strategy Distribution ---
    all_strats = sorted(set(
        list(prev_results.get('strategy', {}).keys()) +
        list(new_results.get('strategy', {}).keys())
    ))
    strat_rows = []
    for s in all_strats:
        pv = prev_results.get('strategy', {}).get(s, 0)
        nv = new_results.get('strategy', {}).get(s, 0)
        hib = s != 'OTHER'
        strat_rows.append((f"Strategy: {s}", pv, nv, hib, "%"))
    metric_table("Strategy Distribution", strat_rows)

    # --- Strategy Consistency ---
    consistency_rows = []
    for key, label, hib in [
        ('strat_all_same', 'All same strategy', True),
        ('strat_2_diff', '2 diff strategies', False),
        ('strat_3_plus', '3+ diff strategies', False),
        ('strat_modal_match', 'Modal match rate', True),
    ]:
        pv = prev_results.get(key)
        nv = new_results.get(key)
        if pv is not None or nv is not None:
            consistency_rows.append((label, pv, nv, hib, "%"))
    if consistency_rows:
        metric_table("Strategy Consistency", consistency_rows)

    # --- Formatting Compliance ---
    fmt_keys = [
        ('has_bullets', 'Bullet points', False),
        ('has_numbered_list', 'Numbered lists', False),
        ('has_section_labels', 'Section labels', False),
        ('has_markdown_headers', 'Markdown headers', False),
    ]
    fmt_rows = []
    for feat, label, hib in fmt_keys:
        pv = prev_results.get('features', {}).get(feat, 0)
        nv = new_results.get('features', {}).get(feat, 0)
        fmt_rows.append((label, pv, nv, hib, "%"))
    metric_table("Formatting Compliance", fmt_rows)

    # --- Opening Behavior ---
    open_rows = []
    for key, label, hib in [
        ('opening_happy_single', "'Happy to help' (single)", True),
        ('opening_happy_follow', "'Happy to help' (follow-up)", False),
        ('opening_direct_follow', 'Direct opening (follow-up)', True),
    ]:
        pv = prev_results.get(key)
        nv = new_results.get(key)
        if pv is not None or nv is not None:
            open_rows.append((label, pv, nv, hib, "%"))
    if open_rows:
        metric_table("Opening Behavior", open_rows)

    # --- Response Length ---
    len_rows = [
        ("Median chars", prev_results.get('length_median'), new_results.get('length_median'), False, ""),
        ("Mean chars", prev_results.get('length_mean'), new_results.get('length_mean'), False, ""),
        ("Median words", prev_results.get('words_median'), new_results.get('words_median'), False, ""),
        ("Mean words", prev_results.get('words_mean'), new_results.get('words_mean'), False, ""),
        ("<= 500 chars", prev_results.get('len_lte_500'), new_results.get('len_lte_500'), True, "%"),
        ("500-1000 chars", prev_results.get('len_500_1000'), new_results.get('len_500_1000'), True, "%"),
        ("> 1000 chars", prev_results.get('len_gt_1000'), new_results.get('len_gt_1000'), False, "%"),
        ("> 1500 chars", prev_results.get('len_gt_1500'), new_results.get('len_gt_1500'), False, "%"),
    ]
    metric_table("Response Length", len_rows)

    # --- Response Features ---
    skip_feats = {'has_bullets', 'has_numbered_list', 'has_section_labels',
                  'has_markdown_headers', 'has_happy_to_help', 'has_log_leak'}
    all_feats = sorted(set(
        list(prev_results.get('features', {}).keys()) +
        list(new_results.get('features', {}).keys())
    ))
    feat_rows = []
    for f in all_feats:
        if f in skip_feats:
            continue
        pv = prev_results.get('features', {}).get(f, 0)
        nv = new_results.get('features', {}).get(f, 0)
        hib = f not in ('has_qa_url', 'has_representative')
        label = f.replace('has_', '').replace('_', ' ').title()
        feat_rows.append((label, pv, nv, hib, "%"))
    if feat_rows:
        metric_table("Response Features", feat_rows)

    # --- Quality ---
    qual_rows = [
        ("Any redundancy", prev_results.get('redundancy'), new_results.get('redundancy'), False, "%"),
        ("Repeated 3-grams", prev_results.get('redundancy_repeated'), new_results.get('redundancy_repeated'), False, "%"),
        ("Similar sentences", prev_results.get('redundancy_similar'), new_results.get('redundancy_similar'), False, "%"),
        ("Robotic echo (4-word)", prev_results.get('echo_4word'), new_results.get('echo_4word'), False, "%"),
        ("Robotic echo (6-word)", prev_results.get('echo_6word'), new_results.get('echo_6word'), False, "%"),
    ]
    metric_table("Quality", qual_rows)

    # --- Consistency ---
    cons_rows = [
        ("Pairwise similarity mean", prev_results.get('consistency_sim_mean'), new_results.get('consistency_sim_mean'), True, ""),
        ("All pairs >90% similar", prev_results.get('consistency_gt90'), new_results.get('consistency_gt90'), True, "%"),
    ]
    metric_table("Cross-run Consistency", cons_rows)

    # --- Latency ---
    lat_rows = []
    for key, label in [('latency_median', 'Median'), ('latency_mean', 'Mean'), ('latency_p90', 'P90')]:
        pv = prev_results.get(key)
        nv = new_results.get(key)
        if pv is not None or nv is not None:
            lat_rows.append((label, pv, nv, False, "s"))
    if lat_rows:
        metric_table("Latency", lat_rows)

    # --- Wins and Regressions ---
    wins = sorted([m for m in sc['details'] if m['winner'] == 'new'],
                  key=lambda m: abs(m['delta']), reverse=True)
    regs = sorted([m for m in sc['details'] if m['winner'] == 'prev'],
                  key=lambda m: abs(m['delta']), reverse=True)

    if wins:
        parts.append("<h2>Wins over Baseline</h2>")
        parts.append("<table><tr><th>Metric</th><th>Baseline</th><th>New</th><th>Delta</th></tr>")
        for m in wins:
            parts.append(f"<tr><td>{m['label']}</td><td>{m['prev']}</td>"
                         f"<td><strong>{m['new']}</strong></td>"
                         f"<td><span style='color:#22c55e;font-weight:600'>{m['delta']:+.1f}</span></td></tr>")
        parts.append("</table>")

    if regs:
        parts.append("<h2>Regressions vs Baseline</h2>")
        parts.append("<table><tr><th>Metric</th><th>Baseline</th><th>New</th><th>Delta</th></tr>")
        for m in regs:
            parts.append(f"<tr><td>{m['label']}</td><td>{m['prev']}</td>"
                         f"<td><strong>{m['new']}</strong></td>"
                         f"<td><span style='color:#ef4444;font-weight:600'>{m['delta']:+.1f}</span></td></tr>")
        parts.append("</table>")

    # --- Response Comparison Appendix ---
    if appendix:
        filter_label = "All utterances" if total_utterances and len(appendix) >= total_utterances \
            else f"Filtered: {len(appendix)} utterances with notable changes"
        parts.append(f"<h2>Response Comparison</h2><p style='color:#6b7280;font-size:0.85rem'>{filter_label}</p>")
        parts.append("""<table style="font-size:0.8rem">
<tr><th style="width:18%">Utterance</th><th style="width:30%">Baseline</th>
<th style="width:30%">New</th><th>Strategy</th><th>Length &Delta;</th><th>Flags</th></tr>""")
        for c in appendix:
            prev_trunc = _esc(c['prev_response'][:300]) + ('...' if len(c['prev_response']) > 300 else '')
            new_trunc = _esc(c['new_response'][:300]) + ('...' if len(c['new_response']) > 300 else '')
            strat_cell = f"{c['prev_strategy']} &rarr; {c['new_strategy']}" \
                if c['prev_strategy'] != c['new_strategy'] else c['new_strategy']
            flags_cell = ', '.join(c['flags']) if c['flags'] else ''
            parts.append(
                f"<tr><td><strong>{_esc(c['utterance'][:80])}</strong></td>"
                f"<td style='font-size:0.75rem'>{prev_trunc}</td>"
                f"<td style='font-size:0.75rem'>{new_trunc}</td>"
                f"<td>{strat_cell}</td>"
                f"<td>{c['len_delta']:+d}</td>"
                f"<td style='color:#dc2626;font-size:0.75rem'>{flags_cell}</td></tr>")
        parts.append("</table>")

    body = "\n".join(parts)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{_esc(title)}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
       background: #f9fafb; color: #1f2937; line-height: 1.6; padding: 2rem;
       max-width: 1100px; margin: 0 auto; }}
h1 {{ font-size: 1.5rem; border-bottom: 2px solid #e5e7eb; padding-bottom: 0.5rem; }}
h2 {{ font-size: 1.15rem; color: #374151; margin-top: 2rem; border-bottom: 1px solid #e5e7eb; padding-bottom: 0.3rem; }}
table {{ width: 100%; border-collapse: collapse; font-size: 0.875rem; margin: 0.75rem 0; }}
th {{ text-align: left; padding: 0.5rem 0.75rem; background: #1f2937; color: white; }}
td {{ padding: 0.45rem 0.75rem; border-bottom: 1px solid #e5e7eb; vertical-align: top; }}
tr:hover td {{ background: #f3f4f6; }}
</style>
</head>
<body>
<h1>{_esc(title)}</h1>
<p style="color:#6b7280;">Regression report &mdash; metrics discovered from data. Scorecard: {sc['wins']} wins, {sc['regressions']} regressions, {sc['ties']} ties.</p>
{body}
</body>
</html>"""


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------

def build_json_output(prev_results, new_results, scorecard, appendix):
    return {
        'baseline': prev_results,
        'new': new_results,
        'scorecard': {
            'wins': scorecard['wins'],
            'regressions': scorecard['regressions'],
            'ties': scorecard['ties'],
            'details': scorecard['details'],
        },
        'appendix': appendix,
    }


# ---------------------------------------------------------------------------
# CLI text summary
# ---------------------------------------------------------------------------

def print_summary(prev_results, new_results, scorecard):
    sc = scorecard
    print(f"\nScorecard: {sc['wins']} wins | {sc['regressions']} regressions | {sc['ties']} ties")
    print(f"\n{'Metric':<35} {'Baseline':>10} {'New':>10} {'Delta':>10}")
    print("-" * 70)
    for key in ['total_rows', 'unique_utterances', 'single_turn', 'follow_up',
                'latency_median', 'length_median', 'words_median',
                'log_leak', 'redundancy', 'echo_4word']:
        pv = prev_results.get(key, 'N/A')
        nv = new_results.get(key, 'N/A')
        delta = ''
        if isinstance(pv, (int, float)) and isinstance(nv, (int, float)):
            delta = f"{nv - pv:+.1f}"
        print(f"{key:<35} {str(pv):>10} {str(nv):>10} {delta:>10}")

    print(f"\nStrategy distribution:")
    all_strats = sorted(set(
        list(prev_results.get('strategy', {}).keys()) +
        list(new_results.get('strategy', {}).keys())
    ))
    for s in all_strats:
        pv = prev_results.get('strategy', {}).get(s, 0)
        nv = new_results.get('strategy', {}).get(s, 0)
        delta = f"{nv - pv:+.1f}"
        print(f"  {s:<30} {pv:>8.1f}% {nv:>8.1f}% {delta:>10}")

    print(f"\nResponse features:")
    all_feats = sorted(set(
        list(prev_results.get('features', {}).keys()) +
        list(new_results.get('features', {}).keys())
    ))
    for f in sorted(all_feats):
        pv = prev_results.get('features', {}).get(f, 0)
        nv = new_results.get('features', {}).get(f, 0)
        delta = f"{nv - pv:+.1f}"
        label = f.replace('has_', '')
        print(f"  {label:<30} {pv:>8.1f}% {nv:>8.1f}% {delta:>10}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Topic-agnostic regression report")
    parser.add_argument("--prev", required=True, help="Baseline CSV")
    parser.add_argument("--new", required=True, help="New results CSV")
    parser.add_argument("--output", required=True, help="Output HTML path")
    parser.add_argument("--json-output", help="Optional JSON sidecar output path")
    parser.add_argument("--title", default="Eval Regression Report")
    parser.add_argument("--full-appendix", action="store_true",
                        help="Show all utterances in appendix (default: only notable changes)")
    args = parser.parse_args()

    prev_rows = load_csv(args.prev)
    new_rows = load_csv(args.new)
    print(f"Baseline: {len(prev_rows)} rows | New: {len(new_rows)} rows")

    prev_results = analyze(prev_rows, "Baseline")
    new_results = analyze(new_rows, "New")

    scorecard = build_scorecard(prev_results, new_results)
    appendix = build_appendix(prev_rows, new_rows, prev_results, new_results,
                              full=args.full_appendix)

    print_summary(prev_results, new_results, scorecard)

    total_utts = len(set(r['utterance'] for r in prev_rows + new_rows))
    html = generate_html(prev_results, new_results, scorecard, appendix, args.title, total_utts)
    with open(args.output, 'w') as f:
        f.write(html)
    print(f"\nHTML report: {args.output}")
    print(f"Appendix: {len(appendix)} utterances shown")

    if args.json_output:
        json_data = build_json_output(prev_results, new_results, scorecard, appendix)
        with open(args.json_output, 'w') as f:
            json.dump(json_data, f, indent=2, default=str)
        print(f"JSON output: {args.json_output}")


if __name__ == "__main__":
    main()
