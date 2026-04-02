import csv
import re
import html as html_mod
from difflib import SequenceMatcher
from collections import Counter, defaultdict
import statistics

PREV_CSV = "/Users/obguzman/Downloads/ESA - Billing Redesign - 3 Step Approach - DEV ESA - 2.24.3 - v21.csv"
NEW_CSV = "/Users/obguzman/Downloads/ESA - Billing PROJ-345 - Prompt Optimization - Sheet10.csv"

def load_csv(path):
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    result = []
    for row in rows:
        mapped = {}
        for c, v in row.items():
            cl = c.lower().strip()
            if cl == 'utterance':
                mapped['utterance'] = v or ''
            elif cl in ('actual outcome', 'agent response'):
                mapped['response'] = v or ''
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

def classify_strategy(response):
    r = response.lower()
    user_part = extract_user_response(response).lower()
    if 'analysis breakdown' in r or 'servicestrategy' in r:
        analysis = r.split('my response:')[0] if 'my response:' in r else r
        strat_match = re.search(r'servicestrategy[:\s*]*\*?\*?\s*(\w+)', analysis)
        if strat_match:
            s = strat_match.group(1).upper()
            if 'EXPLAIN' in s: return 'EXPLAIN'
            if 'IDENTIFY' in s: return 'IDENTIFY_INVOICE'
            if 'ESCALATE' in s or 'TRANSFER' in s: return 'TRANSFER'
            if 'CLARIFY' in s: return 'CLARIFY'
            if 'POST' in s: return 'POST_RESOLUTION'
    if re.search(r"here'?s what i found", user_part) and re.search(r'(breakdown|accrued|taxes and fees)', user_part):
        return 'EXPLAIN'
    if re.search(r'(which invoice|which one|please select|choose one)', user_part):
        return 'IDENTIFY_INVOICE'
    if re.search(r'(connect you|transfer|representative)', user_part):
        return 'TRANSFER'
    if re.search(r'(could you clarify|can you clarify|what.*specifically)', user_part):
        return 'CLARIFY'
    if re.search(r"here'?s what i found", user_part):
        return 'EXPLAIN'
    if re.search(r'\d\.\s+.*invoice', user_part) or re.search(r'\d\.\s+.*\$[\d,]+', user_part):
        return 'IDENTIFY_INVOICE'
    return 'OTHER'

def has_signal(utterance):
    signals = []
    if re.search(r'\$[\d,.]+', utterance): signals.append('amount')
    if re.search(r'(invoice\s*#?\s*\w+|INV-\d+|USI\d+)', utterance, re.I): signals.append('invoice#')
    if re.search(r'(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)', utterance, re.I): signals.append('date')
    return signals

STOPWORDS = set('the a an is are was were i my me we you your it this that to of for in on and or but not with can do does did will would have has had been be am'.split())

def tokenize(text):
    words = re.findall(r'[a-z0-9]+', text.lower())
    return [w for w in words if w not in STOPWORDS and len(w) > 1]

def pairwise_similarity(texts):
    if len(texts) < 2: return []
    pairs = []
    for i in range(len(texts)):
        for j in range(i+1, len(texts)):
            pairs.append(SequenceMatcher(None, texts[i], texts[j]).ratio())
    return pairs

def get_ngrams(text, n):
    words = text.lower().split()
    return [' '.join(words[i:i+n]) for i in range(len(words)-n+1)]

def check_redundancy(text):
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
    trigrams = get_ngrams(text, 3)
    trigram_counts = Counter(trigrams)
    has_repeated = any(c >= 2 for c in trigram_counts.values())
    has_similar = False
    for i in range(len(sentences)):
        for j in range(i+1, len(sentences)):
            if SequenceMatcher(None, sentences[i], sentences[j]).ratio() > 0.6:
                has_similar = True
                break
    return has_repeated, has_similar

def check_robotic_echo(utterance, response, n=4):
    ngrams = get_ngrams(utterance, n)
    skip = {'did this help', 'here s what', 'what i found'}
    for ng in ngrams:
        if ng in skip: continue
        if ng in response.lower(): return True
    return False

def percentile(data, p):
    s = sorted(data)
    k = (len(s) - 1) * p / 100
    f = int(k)
    c = f + 1
    if c >= len(s): return s[-1]
    return s[f] + (k - f) * (s[c] - s[f])

def group_by(rows, key):
    groups = defaultdict(list)
    for r in rows:
        groups[r[key]].append(r)
    return groups

# ============================================================
print("=" * 70)
print("LOADING DATA")
print("=" * 70)

prev = load_csv(PREV_CSV)
new = load_csv(NEW_CSV)

for row in prev:
    row['strategy'] = classify_strategy(row.get('response', ''))
    row['user_response'] = extract_user_response(row.get('response', ''))
for row in new:
    row['strategy'] = classify_strategy(row.get('response', ''))
    row['user_response'] = extract_user_response(row.get('response', ''))

prev_utts = set(r['utterance'] for r in prev)
new_utts = set(r['utterance'] for r in new)
print(f"Previous (2.24.3): {len(prev)} rows, {len(prev_utts)} unique utterances")
print(f"New (Optimized):   {len(new)} rows, {len(new_utts)} unique utterances")

# ============================================================
print("\n" + "=" * 70)
print("1. OVERVIEW")
print("=" * 70)

for label, data in [("Previous (2.24.3)", prev), ("New (Optimized)", new)]:
    latencies = [r['latency_ms']/1000 for r in data if r.get('latency_ms') is not None]
    utts = set(r['utterance'] for r in data)
    print(f"\n  {label}:")
    print(f"    Rows: {len(data)}, Unique utterances: {len(utts)}")
    if latencies:
        print(f"    Latency — median: {statistics.median(latencies):.2f}s, mean: {statistics.mean(latencies):.2f}s, p90: {percentile(latencies, 90):.2f}s, p95: {percentile(latencies, 95):.2f}s")

# ============================================================
print("\n" + "=" * 70)
print("2. STRATEGY MIX")
print("=" * 70)

for label, data in [("Previous (2.24.3)", prev), ("New (Optimized)", new)]:
    n = len(data)
    counts = Counter(r['strategy'] for r in data)
    print(f"\n  {label}:")
    for s in ['EXPLAIN', 'IDENTIFY_INVOICE', 'TRANSFER', 'CLARIFY', 'POST_RESOLUTION', 'OTHER']:
        if counts.get(s, 0) > 0:
            print(f"    {s}: {counts[s]/n*100:.1f}% ({counts[s]})")

# ============================================================
print("\n" + "=" * 70)
print("3. AUTO-SELECTION (Critical)")
print("=" * 70)

for label, data in [("Previous (2.24.3)", prev), ("New (Optimized)", new)]:
    groups = group_by(data, 'utterance')
    always_auto = []
    mixed = []
    never_auto = []
    total_auto = 0
    for utt, rows in groups.items():
        strats = [r['strategy'] for r in rows]
        ac = sum(1 for s in strats if s == 'EXPLAIN')
        if ac == len(strats): always_auto.append(utt); total_auto += ac
        elif ac > 0: mixed.append(utt); total_auto += ac
        else: never_auto.append(utt)
    print(f"\n  {label}:")
    print(f"    Always auto-select: {len(always_auto)}")
    print(f"    Mixed: {len(mixed)}")
    print(f"    Never auto-select: {len(never_auto)}")
    print(f"    Total auto-select instances: {total_auto}")

print("\n  --- Always auto-select utterances (New) ---")
new_groups = group_by(new, 'utterance')
for utt, rows in sorted(new_groups.items()):
    strats = [r['strategy'] for r in rows]
    if all(s == 'EXPLAIN' for s in strats):
        signals = has_signal(utt)
        sig_str = ', '.join(signals) if signals else 'NONE'
        legit = 'Yes' if signals else 'NO'
        short = utt[:90] + '...' if len(utt) > 90 else utt
        print(f"    [{legit}] ({sig_str}) {short}")

# ============================================================
print("\n" + "=" * 70)
print("4. IDENTIFY_INVOICE TEMPLATE ADHERENCE")
print("=" * 70)

for label, data in [("Previous (2.24.3)", prev), ("New (Optimized)", new)]:
    id_rows = [r for r in data if r['strategy'] == 'IDENTIFY_INVOICE']
    n = len(id_rows)
    if n == 0:
        print(f"\n  {label}: No IDENTIFY_INVOICE responses")
        continue
    print(f"\n  {label} ({n} responses):")
    resps = [r['user_response'] for r in id_rows]
    def pct(pattern, flags=re.I): return sum(1 for r in resps if re.search(pattern, r, flags)) / n * 100
    PAT_TRANSITION = r'(i found|here are|i see|your account has|the following)'
    PAT_NUMLIST = r'^\s*1\.'
    PAT_INVNUM = r'(USI|INV|invoice\s*#)'
    PAT_DOLLAR = r'\$[\d,]+'
    PAT_DATE = r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)'
    PAT_LINK = r'\[.*?\]\(http'
    PAT_SELECT = r'(which invoice|which one|please select|like.*details|would you like)'
    PAT_DIDHELP = r'did this help'
    print(f"    Transition line:    {pct(PAT_TRANSITION):.1f}%")
    print(f"    Numbered list:      {pct(PAT_NUMLIST, re.M):.1f}%")
    print(f"    Invoice numbers:    {pct(PAT_INVNUM):.1f}%")
    print(f"    Dollar amounts:     {pct(PAT_DOLLAR):.1f}%")
    print(f"    Dates:              {pct(PAT_DATE):.1f}%")
    print(f"    Clickable links:    {pct(PAT_LINK):.1f}%")
    print(f"    Selection prompt:   {pct(PAT_SELECT):.1f}%")
    print(f"    'Did this help?':   {pct(PAT_DIDHELP):.1f}% (wrong for IDENTIFY)")
    clean = sum(1 for r in resps if not re.search(r'(accrued|taxes and fees|breakdown)', r, re.I)) / n * 100
    print(f"    Clean list:         {clean:.1f}%")

# ============================================================
print("\n" + "=" * 70)
print("5. EXPLAIN TEMPLATE ADHERENCE")
print("=" * 70)

for label, data in [("Previous (2.24.3)", prev), ("New (Optimized)", new)]:
    ex_rows = [r for r in data if r['strategy'] == 'EXPLAIN']
    n = len(ex_rows)
    if n == 0:
        print(f"\n  {label}: No EXPLAIN responses")
        continue
    print(f"\n  {label} ({n} responses):")
    resps = [r['user_response'] for r in ex_rows]
    def pct(pattern, flags=re.I): return sum(1 for r in resps if re.search(pattern, r, flags)) / n * 100
    PAT_HWIF = r"here'?s what i found"
    PAT_INVID = r'(USI|INV|invoice\s*#)'
    PAT_DOLLAR = r'\$[\d,]+'
    PAT_BREAKDOWN = r'(accrued|breakdown|line.?item)'
    PAT_TAX = r'(taxes and fees|remaining.*covers)'
    PAT_INVDL = r'download.*invoice|invoice.*\[here\]'
    PAT_ITEMRPT = r'itemized.*report|report.*\[here\]'
    PAT_QA = r'qa-|staging'
    PAT_POLICY = r'(policy|click|sponsor|campaign|budget|paused|billing cycle|accrue)'
    PAT_DIDHELP = r'did this help'
    print(f"    'Here's what I found': {pct(PAT_HWIF):.1f}%")
    print(f"    Invoice ID present:    {pct(PAT_INVID):.1f}%")
    print(f"    Dollar amount:         {pct(PAT_DOLLAR):.1f}%")
    print(f"    Line-item breakdown:   {pct(PAT_BREAKDOWN):.1f}%")
    print(f"    Tax/fees explanation:   {pct(PAT_TAX):.1f}%")
    print(f"    Invoice download link: {pct(PAT_INVDL):.1f}%")
    print(f"    Itemized report link:  {pct(PAT_ITEMRPT):.1f}%")
    print(f"    QA/staging URLs:       {pct(PAT_QA):.1f}%")
    print(f"    Policy section:        {pct(PAT_POLICY):.1f}%")
    print(f"    'Did this help?':      {pct(PAT_DIDHELP):.1f}%")

# ============================================================
print("\n" + "=" * 70)
print("6. TRANSFER TEMPLATE ADHERENCE")
print("=" * 70)

for label, data in [("Previous (2.24.3)", prev), ("New (Optimized)", new)]:
    tr_rows = [r for r in data if r['strategy'] == 'TRANSFER']
    n = len(tr_rows)
    if n == 0:
        print(f"\n  {label}: No TRANSFER responses")
        continue
    print(f"\n  {label} ({n} responses):")
    resps = [r['user_response'] for r in tr_rows]
    clean_t = sum(1 for r in resps if len(r) < 200 and not re.search(r'(invoice|breakdown|accrued)', r, re.I)) / n * 100
    print(f"    Clean transfer:       {clean_t:.1f}%")
    print(f"    With context:         {100-clean_t:.1f}%")
    print(f"    No invoice breakdown: {sum(1 for r in resps if not re.search(r'(accrued|breakdown|line.?item)', r, re.I))/n*100:.1f}%")

# ============================================================
print("\n" + "=" * 70)
print("7. MARKDOWN & FORMATTING")
print("=" * 70)

for label, data in [("Previous (2.24.3)", prev), ("New (Optimized)", new)]:
    n = len(data)
    resps = [r['user_response'] for r in data]
    print(f"\n  {label}:")
    bold = sum(1 for r in resps if '**' in r) / n * 100
    numlist = sum(1 for r in resps if re.search(r'^\s*\d+\.', r, re.M)) / n * 100
    bullets = sum(1 for r in resps if re.search(r'^\s*[-*]\s', r, re.M)) / n * 100
    clinks = sum(1 for r in resps if re.search(r'\[.*?\]\(http', r)) / n * 100
    qa = sum(1 for r in resps if re.search(r'qa-|staging', r, re.I)) / n * 100
    print(f"    Bold text:       {bold:.1f}%")
    print(f"    Numbered lists:  {numlist:.1f}%")
    print(f"    Bullets:         {bullets:.1f}%")
    print(f"    Clickable links: {clinks:.1f}%")
    print(f"    QA/broken URLs:  {qa:.1f}%")

# ============================================================
print("\n" + "=" * 70)
print("8. LENGTH")
print("=" * 70)

for label, data in [("Previous (2.24.3)", prev), ("New (Optimized)", new)]:
    lengths = [len(r['user_response']) for r in data]
    print(f"\n  {label}:")
    print(f"    Median: {statistics.median(lengths):.0f} chars")
    print(f"    Mean:   {statistics.mean(lengths):.0f} chars")
    print(f"    ≤1500:  {sum(1 for l in lengths if l <= 1500)/len(lengths)*100:.1f}%")
    print(f"    >2000:  {sum(1 for l in lengths if l > 2000)}")

# ============================================================
print("\n" + "=" * 70)
print("9. STRATEGY CONSISTENCY (same utterance)")
print("=" * 70)

for label, data in [("Previous (2.24.3)", prev), ("New (Optimized)", new)]:
    groups = group_by(data, 'utterance')
    multi = {u: rows for u, rows in groups.items() if len(rows) >= 2}
    if not multi:
        print(f"\n  {label}: Only single-run utterances — skipping consistency")
        continue
    all_same = sum(1 for rows in multi.values() if len(set(r['strategy'] for r in rows)) == 1)
    two_diff = sum(1 for rows in multi.values() if len(set(r['strategy'] for r in rows)) == 2)
    three_plus = sum(1 for rows in multi.values() if len(set(r['strategy'] for r in rows)) >= 3)
    total_runs = sum(len(rows) for rows in multi.values())
    modal_matches = 0
    for rows in multi.values():
        strats = [r['strategy'] for r in rows]
        modal = Counter(strats).most_common(1)[0][0]
        modal_matches += sum(1 for s in strats if s == modal)
    print(f"\n  {label} ({len(multi)} utterances with 2+ runs):")
    print(f"    All same strategy:   {all_same} ({all_same/len(multi)*100:.0f}%)")
    print(f"    2 different:         {two_diff}")
    print(f"    3+ different:        {three_plus}")
    print(f"    Runs matching modal: {modal_matches/total_runs*100:.1f}%")

# ============================================================
print("\n" + "=" * 70)
print("10. ANSWER CONSISTENCY (EXPLAIN, same utterance)")
print("=" * 70)

for label, data in [("Previous (2.24.3)", prev), ("New (Optimized)", new)]:
    ex = [r for r in data if r['strategy'] == 'EXPLAIN']
    groups = group_by(ex, 'utterance')
    multi = {u: rows for u, rows in groups.items() if len(rows) >= 2}
    if not multi:
        print(f"\n  {label}: Not enough multi-run EXPLAIN utterances")
        continue
    all_sims = []
    gt08 = 0; gt09 = 0
    length_ratios = []
    for rows in multi.values():
        texts = [r['user_response'] for r in rows]
        lens = [len(t) for t in texts]
        if max(lens) > 0: length_ratios.append(min(lens)/max(lens))
        sims = pairwise_similarity(texts)
        all_sims.extend(sims)
        if sims and all(s > 0.8 for s in sims): gt08 += 1
        if sims and all(s > 0.9 for s in sims): gt09 += 1
    print(f"\n  {label} ({len(multi)} utterances):")
    if length_ratios: print(f"    Length ratio (min/max): {statistics.mean(length_ratios):.3f}")
    if all_sims:
        print(f"    Pairwise sim mean:     {statistics.mean(all_sims):.3f}")
        print(f"    Pairwise sim median:   {statistics.median(all_sims):.3f}")
        print(f"    % all pairs > 0.8:     {gt08/len(multi)*100:.1f}%")
        print(f"    % all pairs > 0.9:     {gt09/len(multi)*100:.1f}%")

# ============================================================
print("\n" + "=" * 70)
print("11. RESPONSE SIMILARITY (all strategies)")
print("=" * 70)

for label, data in [("Previous (2.24.3)", prev), ("New (Optimized)", new)]:
    groups = group_by(data, 'utterance')
    multi = {u: rows for u, rows in groups.items() if len(rows) >= 2}
    if not multi:
        print(f"\n  {label}: Only single-run utterances — skipping")
        continue
    sc = 0; tc = 0; tpc = 0
    for rows in multi.values():
        texts = [r['user_response'] for r in rows]
        sims = pairwise_similarity(texts)
        if sims and min(sims) > 0.9: sc += 1
        elif sims and min(sims) > 0.5: tc += 1
        else: tpc += 1
    total = len(multi)
    print(f"\n  {label} ({total} utterances):")
    print(f"    All >90% similar:  {sc} ({sc/total*100:.0f}%)")
    print(f"    2 clusters:        {tc}")
    print(f"    3+ clusters:       {tpc} ({tpc/total*100:.0f}%)")

# ============================================================
print("\n" + "=" * 70)
print("12. QUALITY (Answer-Question Overlap)")
print("=" * 70)

for label, data in [("Previous (2.24.3)", prev), ("New (Optimized)", new)]:
    overlaps = []
    for r in data:
        qt = set(tokenize(r['utterance']))
        at = set(tokenize(r['user_response']))
        if qt: overlaps.append(len(qt & at) / len(qt))
    print(f"\n  {label}:")
    print(f"    Mean overlap:  {statistics.mean(overlaps):.3f}")
    print(f"    % > 0.5:       {sum(1 for o in overlaps if o > 0.5)/len(overlaps)*100:.1f}%")
    print(f"    % < 0.2:       {sum(1 for o in overlaps if o < 0.2)/len(overlaps)*100:.1f}%")

# ============================================================
print("\n" + "=" * 70)
print("13. REDUNDANCY")
print("=" * 70)

for label, data in [("Previous (2.24.3)", prev), ("New (Optimized)", new)]:
    n = len(data)
    any_r = 0; rep = 0; sim = 0
    for r in data:
        rp, sm = check_redundancy(r['user_response'])
        if rp: rep += 1
        if sm: sim += 1
        if rp or sm: any_r += 1
    print(f"\n  {label}:")
    print(f"    Any redundancy:    {any_r/n*100:.1f}%")
    print(f"    Repeated phrases:  {rep/n*100:.1f}%")
    print(f"    Similar sentences: {sim/n*100:.1f}%")

# ============================================================
print("\n" + "=" * 70)
print("14. ROBOTIC ECHO")
print("=" * 70)

for label, data in [("Previous (2.24.3)", prev), ("New (Optimized)", new)]:
    n = len(data)
    e4 = sum(1 for r in data if check_robotic_echo(r['utterance'], r['user_response'], 4)) / n * 100
    e6 = sum(1 for r in data if check_robotic_echo(r['utterance'], r['user_response'], 6)) / n * 100
    print(f"\n  {label}:")
    print(f"    4+ word echo: {e4:.1f}%")
    print(f"    6+ word echo: {e6:.1f}%")

# ============================================================
print("\n" + "=" * 70)
print("15. SUPPORT WITHOUT TRANSFER & LEARN MORE")
print("=" * 70)

for label, data in [("Previous (2.24.3)", prev), ("New (Optimized)", new)]:
    swt = sum(1 for r in data if re.search(r'(support|contact)', r['user_response'], re.I) and not re.search(r'(connect you|transfer|would you like me to)', r['user_response'], re.I))
    ex = [r for r in data if r['strategy'] == 'EXPLAIN']
    ne = len(ex) if ex else 1
    lm = sum(1 for r in ex if re.search(r'learn more', r['user_response'], re.I)) / ne * 100
    print(f"\n  {label}:")
    print(f"    Support w/o transfer:  {swt}")
    print(f"    Learn More in EXPLAIN: {lm:.1f}%")

# ============================================================
print("\n" + "=" * 70)
print("BONUS: ANALYSIS BREAKDOWN ADHERENCE (New only)")
print("=" * 70)

n = len(new)
print(f"  Analysis Breakdown present: {sum(1 for r in new if re.search(r'analysis breakdown', r['response'], re.I))/n*100:.1f}%")
print(f"  ServiceStrategy declared:   {sum(1 for r in new if re.search(r'servicestrategy', r['response'], re.I))/n*100:.1f}%")
print(f"  Consistency check:          {sum(1 for r in new if re.search(r'consistency check', r['response'], re.I))/n*100:.1f}%")
print(f"  Signal count present:       {sum(1 for r in new if re.search(r'signal count', r['response'], re.I))/n*100:.1f}%")
print(f"  'My Response' separator:    {sum(1 for r in new if re.search(r'\\*\\*my response', r['response'], re.I))/n*100:.1f}%")

print("\n" + "=" * 70)
print("DONE")
print("=" * 70)
