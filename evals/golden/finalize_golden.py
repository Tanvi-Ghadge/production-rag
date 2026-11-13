"""
Phase 0b: Add 45 new questions to golden.jsonl.
Phase 0c: Create stratified dev/test split.
Phase 0d: Write selection rule to docs/decisions.md.

New questions:
  - IDs g121..g165
  - reference_answer = first 500 chars of source passage (extractive gold)
  - valid_chunk_ids = [primary_chunk_id] (secondary added for multi_hop)
  - review_status = 'draft-auto-generated'
  - 20% hand-check flag set on random 9 of 45

Split: stratified by category, ~70% dev / ~30% test, seed=42.
Commits split to evals/golden/split.json.
"""
import json, random, math, os
from datetime import datetime, timezone

random.seed(42)

# ── 1. Load new drafts ─────────────────────────────────────────────────────────
drafts = [json.loads(l) for l in open('evals/golden/new_questions_clean.jsonl', encoding='utf-8')]

# ── 2. Load chunk lookup for reference answers ─────────────────────────────────
chunk_lookup = {}
for line in open('data/index/chunks.jsonl', encoding='utf-8'):
    c = json.loads(line)
    chunk_lookup[c['chunk_id']] = c

# ── 3. Load existing golden ────────────────────────────────────────────────────
existing = [json.loads(l) for l in open('evals/golden/golden.jsonl', encoding='utf-8')]
print(f'Existing rows: {len(existing)}')

# ── 4. Build new rows ──────────────────────────────────────────────────────────
# Mark 9 random drafts (20%) for hand-check
hand_check_indices = set(random.sample(range(len(drafts)), 9))

new_rows = []
for i, d in enumerate(drafts):
    idx = 121 + i
    qid = f'g{idx:03d}'

    cid = d['primary_chunk_id']
    cid2 = d.get('secondary_chunk_id', '')
    chunk = chunk_lookup.get(cid, {})

    source_text = chunk.get('text', d.get('source_text_preview', ''))
    ref_answer = source_text[:500].strip()

    valid_ids = [cid]
    if cid2 and cid2 in chunk_lookup:
        valid_ids.append(cid2)

    source_passages = []
    for vid in valid_ids:
        if vid in chunk_lookup:
            ck = chunk_lookup[vid]
            source_passages.append({
                'chunk_id': vid,
                'document_id': ck.get('document_id', d.get('doc', '')),
                'page': ck.get('page_start', 0),
                'section_path': ck.get('section_path', ''),
                'tenant': ck.get('tenant', ''),
                'text': ck.get('text', '')[:600],
            })

    row = {
        'id': qid,
        'question': d['question'],
        'category': d['category'],
        'reference_answer': ref_answer,
        'source_passages': source_passages,
        'valid_chunk_ids': valid_ids,
        'review_status': 'draft-auto-generated',
        'hand_check_required': (i in hand_check_indices),
        'generated_at': datetime.now(timezone.utc).isoformat(),
    }
    new_rows.append(row)

print(f'New rows to add: {len(new_rows)}')
print(f'Hand-check required: {sum(1 for r in new_rows if r["hand_check_required"])}')
by_cat = {}
for r in new_rows:
    by_cat[r['category']] = by_cat.get(r['category'], 0) + 1
print('New by category:', by_cat)

# ── 5. Write updated golden.jsonl ──────────────────────────────────────────────
all_rows = existing + new_rows
with open('evals/golden/golden.jsonl', 'w', encoding='utf-8') as f:
    for r in all_rows:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')
print(f'golden.jsonl now has {len(all_rows)} rows')

# ── 6. Stratified dev/test split ──────────────────────────────────────────────
# Only split answerable questions (exclude unanswerable/adversarial from metric tuning)
# But include all in the file for completeness. Split is 70/30 within each category.

ANSWERABLE = {'factoid', 'multi_hop', 'table_lookup', 'version_sensitive'}

by_category = {}
for r in all_rows:
    cat = r['category']
    by_category.setdefault(cat, []).append(r['id'])

dev_ids = []
test_ids = []

for cat, ids in by_category.items():
    shuffled = ids[:]
    random.shuffle(shuffled)
    if cat in ANSWERABLE:
        n_test = max(1, math.floor(len(shuffled) * 0.30))
        test_ids.extend(shuffled[:n_test])
        dev_ids.extend(shuffled[n_test:])
    else:
        # unanswerable / adversarial: put all in dev (don't evaluate on test for these)
        dev_ids.extend(shuffled)

split = {
    'seed': 42,
    'created_at': datetime.now(timezone.utc).isoformat(),
    'selection_rule': 'Winning config = best Recall@5 on dev; Recall@20 as tiebreaker. Test run once, at the very end.',
    'dev': sorted(dev_ids),
    'test': sorted(test_ids),
    'dev_count': len(dev_ids),
    'test_count': len(test_ids),
    'by_category': {
        cat: {
            'dev': sorted([i for i in dev_ids if any(r['id'] == i and r['category'] == cat for r in all_rows)]),
            'test': sorted([i for i in test_ids if any(r['id'] == i and r['category'] == cat for r in all_rows)]),
        }
        for cat in by_category
    },
}

os.makedirs('evals/golden', exist_ok=True)
with open('evals/golden/split.json', 'w', encoding='utf-8') as f:
    json.dump(split, f, indent=2)
print(f'Split: dev={len(dev_ids)}, test={len(test_ids)}')

# Category breakdown
for cat, ids in by_category.items():
    dev_n = len([i for i in dev_ids if i in set(ids)])
    test_n = len([i for i in test_ids if i in set(ids)])
    print(f'  {cat}: {len(ids)} total → dev={dev_n} test={test_n}')

# ── 7. Write selection rule ────────────────────────────────────────────────────
os.makedirs('docs', exist_ok=True)
decisions_path = 'docs/decisions.md'
with open(decisions_path, 'w', encoding='utf-8') as f:
    f.write('# Engineering Decisions Log\n\n')
    f.write('## D-001 — Winning Configuration Selection Rule (2026-11-13)\n\n')
    f.write('**Rule (written before any evaluation run):**\n\n')
    f.write('The winning configuration is chosen by **Recall@5 on the dev split**.\n')
    f.write('Recall@20 is the tiebreaker if two configs are within Wilson 95% CI overlap.\n')
    f.write('The test split is run **once**, at the very end, on the single selected config.\n\n')
    f.write('**Metric levels reported (per config):**\n')
    f.write('- Strict chunk-level Recall@5 and Recall@20 (primary)\n')
    f.write('- Section-level Recall@5 (parent_id match)\n')
    f.write('- Document-level Recall@5\n')
    f.write('- MRR@10 (chunk level)\n')
    f.write('All with 95% Wilson confidence intervals.\n\n')
    f.write('## D-002 — Question Set Freeze (2026-11-13)\n\n')
    f.write('- 40 heading-leaking factoid questions rewritten (see CHANGELOG.md)\n')
    f.write('- 45 new questions added (10 factoid, 15 table, 10 version, 10 multi_hop)\n')
    f.write('- 9 of 45 new questions flagged for hand-review\n')
    f.write('- Stratified 70/30 dev/test split, seed=42, committed to split.json\n')
    f.write('- Test split LOCKED — do not evaluate on it until final config is chosen\n')

print(f'Selection rule written to {decisions_path}')
print('Done.')
