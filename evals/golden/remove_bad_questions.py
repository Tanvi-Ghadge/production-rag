"""Remove 5 bad hand-check questions, update CHANGELOG."""
import json
from datetime import datetime, timezone

REJECT_IDS = {"g122", "g127", "g135", "g136", "g138"}
REJECT_REASONS = {
    "g122": "Wrong doc tag: question says kyc_md_2016 but passage is UAPA §51A content from kyc_md_2025",
    "g127": "Question/passage mismatch: question about V-CIP standards, passage about Aadhaar OTP conversion",
    "g135": "Passage is letter salutation, not a threshold/limit",
    "g136": "Passage is circular header text, not a data table",
    "g138": "Passage is RBI website footer — no regulatory content",
}

rows = [json.loads(l) for l in open('evals/golden/golden.jsonl', encoding='utf-8')]
before = len(rows)
kept = [r for r in rows if r['id'] not in REJECT_IDS]
removed = [r for r in rows if r['id'] in REJECT_IDS]
print(f"Removing {len(removed)} rows: {[r['id'] for r in removed]}")

with open('evals/golden/golden.jsonl', 'w', encoding='utf-8') as f:
    for r in kept:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')

print(f"golden.jsonl: {before} → {len(kept)} rows")

# Update split.json to remove rejected IDs
split = json.load(open('evals/golden/split.json'))
orig_dev = len(split['dev'])
orig_test = len(split['test'])
split['dev'] = [i for i in split['dev'] if i not in REJECT_IDS]
split['test'] = [i for i in split['test'] if i not in REJECT_IDS]
split['dev_count'] = len(split['dev'])
split['test_count'] = len(split['test'])
json.dump(split, open('evals/golden/split.json', 'w'), indent=2)
print(f"split.json dev: {orig_dev}→{len(split['dev'])}, test: {orig_test}→{len(split['test'])}")

# Append to CHANGELOG
with open('evals/golden/CHANGELOG.md', 'a', encoding='utf-8') as f:
    f.write(f'\n## {datetime.now(timezone.utc).date()} — Hand-check removals\n\n')
    f.write('Removed 5 auto-generated questions that failed hand-check:\n\n')
    for r in removed:
        f.write(f'- **{r["id"]}** ({r["category"]}): {REJECT_REASONS[r["id"]]}\n')
    f.write('\nPassed: g128, g129, g155, g161 remain.\n')

print('CHANGELOG updated. Done.')
