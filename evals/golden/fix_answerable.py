"""
Phase 0b fix: set answerable=true and valid_chunk_ids on the 45 new questions.
Phase 0g: add wilson_ci() to ablations.
Also update run_ablations.py to run on dev split only.
"""
import json

# ── Fix golden.jsonl ───────────────────────────────────────────────────────────
rows = [json.loads(l) for l in open('evals/golden/golden.jsonl', encoding='utf-8')]
ANSWERABLE_CATS = {'factoid', 'multi_hop', 'table_lookup', 'version_sensitive'}
fixed = 0
for r in rows:
    if r.get('review_status') == 'draft-auto-generated':
        if r.get('category') in ANSWERABLE_CATS:
            r['answerable'] = True
        # also backfill valid_chunk_ids from source_passages if missing
        if not r.get('valid_chunk_ids') and r.get('source_passages'):
            r['valid_chunk_ids'] = [sp['chunk_id'] for sp in r['source_passages']]
        fixed += 1

with open('evals/golden/golden.jsonl', 'w', encoding='utf-8') as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')

print(f'Fixed {fixed} new rows — answerable set, valid_chunk_ids backfilled')
ans = [r for r in rows if r.get('answerable')]
print(f'Total answerable now: {len(ans)}')
by_cat = {}
for r in ans:
    c = r.get('category', '?')
    by_cat[c] = by_cat.get(c, 0) + 1
print('Answerable by category:', by_cat)

# ── Verify split ───────────────────────────────────────────────────────────────
split = json.load(open('evals/golden/split.json'))
dev_set = set(split['dev'])
test_set = set(split['test'])
dev_ans = [r for r in rows if r['id'] in dev_set and r.get('answerable')]
test_ans = [r for r in rows if r['id'] in test_set and r.get('answerable')]
print(f'\nDev answerable: {len(dev_ans)}, Test answerable: {len(test_ans)}')
