import re
import json
import sys

path = sys.argv[1] if len(sys.argv) > 1 else '/tmp/smoke_test_1.json'

raw = open(path, 'rb').read().decode('utf-8', errors='replace')
clean = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', raw)
decoder = json.JSONDecoder(strict=False)
data = decoder.decode(clean)
msgs = data.get('result', {}).get('messages', [])

for m in msgs:
    msg = m.get('message', '')
    parts = re.split(r'\*\*My Response:\*\*', msg, flags=re.IGNORECASE)
    user_response = parts[-1].strip() if len(parts) > 1 else msg.strip()

    print(f'FULL: {len(msg)} chars | HAS ANALYSIS: {len(parts) > 1}')
    print('--- USER RESPONSE ---')
    print(user_response[:1500])
    print()

    checks = [
        ("Heres what I found", r"here.s what i found", False),
        ("Did this help", r"did this help", False),
        ("Invoice USI", r"USI", False),
        ("Dollar amount", r"\$[\d,]+", False),
        ("Clickable link", r"\[.*?\]\(http", False),
        ("No escalation offer", r"representative", True),
    ]
    print('--- CHECKS ---')
    for label, pat, is_negative in checks:
        found = bool(re.search(pat, user_response, re.I))
        passed = (not found) if is_negative else found
        print(f'  {"PASS" if passed else "FAIL"} {label}')
