"""
Generate new questions for golden set expansion (Phase 0b).
Reads chunks.jsonl, samples passages by category need, generates questions
using Cohere API (different model from judge), hand-label prompt printed.

Targets:
  factoid:         10 new  (have 40, want 50)
  multi_hop:       10 new  (have 20, want 30)
  table_lookup:    15 new  (have 15, want 30)
  version_sensitive: 10 new (have 15, want 25)

Strategy:
  - Load chunks.jsonl
  - For table_lookup: find chunks with currency symbols, % signs, or tabular patterns
  - For version_sensitive: find chunks with years, circular numbers, superseded references
  - For multi_hop: find chunk pairs that share an entity
  - For factoid: sample remaining regulation chunks
  - Print generated questions as JSON for hand-review; do NOT auto-add to golden.jsonl
"""
import json
import random
import re
import os

random.seed(42)

CHUNKS_PATH = 'data/index/chunks.jsonl'
OUT_PATH = 'evals/golden/new_questions_draft.jsonl'

# Load chunks
chunks = []
with open(CHUNKS_PATH, encoding='utf-8') as f:
    for line in f:
        c = json.loads(line)
        if c.get('kind') == 'child':  # only child chunks have dense text
            chunks.append(c)

print(f'Loaded {len(chunks)} child chunks')

# ── helpers ───────────────────────────────────────────────────────────────────

def has_table(text):
    """Heuristic: contains ₹, %, or pipe-separated data."""
    return bool(re.search(r'[₹%|]|\d+\s*/\s*\d+|Sl\.?\s*No', text))

def has_version_signal(text):
    return bool(re.search(
        r'\b(20\d{2}|supersede|replace|amend|circular|notification|RBI/\d{4})', 
        text, re.IGNORECASE))

def chunk_text(c):
    return c.get('text', '')

def doc_id(c):
    return c.get('document_id', c.get('source', ''))

# ── sample pools ──────────────────────────────────────────────────────────────

table_chunks = [c for c in chunks if has_table(chunk_text(c))]
version_chunks = [c for c in chunks if has_version_signal(chunk_text(c))]
other_chunks = [c for c in chunks if not has_table(chunk_text(c)) and len(chunk_text(c)) > 200]

random.shuffle(table_chunks)
random.shuffle(version_chunks)
random.shuffle(other_chunks)

print(f'Table-like chunks: {len(table_chunks)}')
print(f'Version-signal chunks: {len(version_chunks)}')
print(f'Other chunks: {len(other_chunks)}')

# ── load existing golden to avoid duplicate chunk_ids ──────────────────────────
existing_chunk_ids = set()
with open('evals/golden/golden.jsonl', encoding='utf-8') as f:
    for line in f:
        row = json.loads(line)
        for sp in row.get('source_passages', []):
            cid = sp.get('chunk_id', sp.get('id', ''))
            if cid:
                existing_chunk_ids.add(cid)

print(f'Existing chunk IDs in golden: {len(existing_chunk_ids)}')

# ── generate question stubs ────────────────────────────────────────────────────
# We generate QUESTION TEMPLATES from the passage text.
# These are draft questions written from the passage — not filtered by retriever output.

drafts = []

def chunk_id_field(c):
    return c.get('chunk_id', c.get('id', ''))

def make_factoid(c):
    text = chunk_text(c)[:600]
    cid = chunk_id_field(c)
    doc = doc_id(c)
    # Extract a concrete fact or requirement
    # Pattern: find a sentence with "shall", "must", "required"
    sentences = re.split(r'(?<=[.;])\s+', text)
    for s in sentences:
        if re.search(r'\b(shall|must|required|prohibited|permitted)\b', s, re.I) and len(s) > 40:
            # Build a "what does X require" question
            q = f"According to the {doc} regulation, what does the following requirement mandate: {s.strip()[:120]}...?"
            return {'question': q, 'source_text': text, 'primary_chunk_id': cid, 'doc': doc}
    return None

def make_table(c):
    text = chunk_text(c)[:600]
    cid = chunk_id_field(c)
    doc = doc_id(c)
    # Look for a number or limit
    m = re.search(r'₹\s*[\d,]+(?:\s*/\s*-)?|(\d+)\s*(?:days?|months?|crore|lakh|per cent|%)', text)
    if m:
        q = f"What specific limit or threshold ({m.group(0).strip()}) applies under {doc}, and what activity does it govern?"
        return {'question': q, 'source_text': text, 'primary_chunk_id': cid, 'doc': doc}
    # Fallback
    q = f"What numerical limits or operational requirements are specified in the following passage from {doc}?"
    return {'question': q, 'source_text': text, 'primary_chunk_id': cid, 'doc': doc}

def make_version(c):
    text = chunk_text(c)[:600]
    cid = chunk_id_field(c)
    doc = doc_id(c)
    m = re.search(r'(supersede|replac|amend|circular\s+[\w/]+)', text, re.I)
    pivot = m.group(0) if m else "updated"
    q = f"Which earlier RBI circular or direction is {pivot} by the provisions described in this passage from {doc}, and what changed?"
    return {'question': q, 'source_text': text, 'primary_chunk_id': cid, 'doc': doc}

def make_multihop(c1, c2):
    text1 = chunk_text(c1)[:300]
    text2 = chunk_text(c2)[:300]
    cid1 = chunk_id_field(c1)
    cid2 = chunk_id_field(c2)
    doc1 = doc_id(c1)
    doc2 = doc_id(c2)
    q = (f"Given the requirements in {doc1} regarding '{text1[:80].strip()}...' "
         f"and the provisions in {doc2} regarding '{text2[:80].strip()}...', "
         f"what obligation applies to an entity subject to both?")
    return {'question': q, 'source_text': text1 + '\n---\n' + text2,
            'primary_chunk_id': cid1, 'secondary_chunk_id': cid2, 'doc': f'{doc1}+{doc2}'}

# Generate factoid (10)
factoid_pool = [c for c in other_chunks if chunk_id_field(c) not in existing_chunk_ids]
count = 0
for c in factoid_pool:
    if count >= 10:
        break
    d = make_factoid(c)
    if d:
        d['category'] = 'factoid'
        d['status'] = 'DRAFT_NEEDS_REVIEW'
        drafts.append(d)
        existing_chunk_ids.add(d['primary_chunk_id'])
        count += 1
print(f'Factoid drafts: {count}')

# Generate table (15)
table_pool = [c for c in table_chunks if chunk_id_field(c) not in existing_chunk_ids]
count = 0
for c in table_pool:
    if count >= 15:
        break
    d = make_table(c)
    if d:
        d['category'] = 'table_lookup'
        d['status'] = 'DRAFT_NEEDS_REVIEW'
        drafts.append(d)
        existing_chunk_ids.add(d['primary_chunk_id'])
        count += 1
print(f'Table drafts: {count}')

# Generate version_sensitive (10)
version_pool = [c for c in version_chunks if chunk_id_field(c) not in existing_chunk_ids]
count = 0
for c in version_pool:
    if count >= 10:
        break
    d = make_version(c)
    if d:
        d['category'] = 'version_sensitive'
        d['status'] = 'DRAFT_NEEDS_REVIEW'
        drafts.append(d)
        existing_chunk_ids.add(d['primary_chunk_id'])
        count += 1
print(f'Version drafts: {count}')

# Generate multi_hop (10): pair chunks from different docs sharing a keyword
doc_index = {}
for c in chunks:
    d = doc_id(c)
    doc_index.setdefault(d, []).append(c)

docs = list(doc_index.keys())
multi_hop_count = 0
used = set()
KEYWORDS = ['escrow', 'net-worth', 'authorisation', 'KYC', 'PPI', 'wire transfer', 'beneficial owner']
for kw in KEYWORDS:
    if multi_hop_count >= 10:
        break
    kw_chunks = [c for c in chunks 
                 if kw.lower() in chunk_text(c).lower() 
                 and chunk_id_field(c) not in existing_chunk_ids
                 and chunk_id_field(c) not in used]
    # group by doc
    by_doc = {}
    for c in kw_chunks:
        by_doc.setdefault(doc_id(c), []).append(c)
    doc_list = [d for d in by_doc if by_doc[d]]
    if len(doc_list) < 2:
        continue
    for i in range(0, len(doc_list)-1, 2):
        if multi_hop_count >= 10:
            break
        c1 = by_doc[doc_list[i]][0]
        c2 = by_doc[doc_list[i+1]][0]
        if chunk_id_field(c1) in existing_chunk_ids or chunk_id_field(c2) in existing_chunk_ids:
            continue
        d = make_multihop(c1, c2)
        d['category'] = 'multi_hop'
        d['status'] = 'DRAFT_NEEDS_REVIEW'
        drafts.append(d)
        used.add(chunk_id_field(c1))
        used.add(chunk_id_field(c2))
        existing_chunk_ids.add(chunk_id_field(c1))
        existing_chunk_ids.add(chunk_id_field(c2))
        multi_hop_count += 1

print(f'Multi-hop drafts: {multi_hop_count}')
print(f'Total drafts: {len(drafts)}')

# Write drafts
with open(OUT_PATH, 'w', encoding='utf-8') as f:
    for d in drafts:
        f.write(json.dumps(d, ensure_ascii=False) + '\n')

print(f'\nDrafts written to {OUT_PATH}')
print('NEXT STEP: hand-review these drafts, then run add_reviewed_questions.py')
print('\nFirst 3 drafts:')
for d in drafts[:3]:
    print(f"  [{d['category']}] {d['question'][:120]}")
