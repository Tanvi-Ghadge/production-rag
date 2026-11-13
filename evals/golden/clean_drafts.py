"""
Turn the 45 raw draft stubs into clean, natural questions.
Works entirely from source_text — no retriever output used.
Outputs: evals/golden/new_questions_clean.jsonl  (45 rows, DRAFT_NEEDS_REVIEW)
"""
import json, re, random
random.seed(42)

drafts = [json.loads(l) for l in open('evals/golden/new_questions_draft.jsonl', encoding='utf-8')]
print(f'Drafts in: {len(drafts)}')

def clean_text(t):
    # Remove page number artifacts like "26 " at start
    return re.sub(r'^\d+\s+', '', t.strip())

def first_requirement_sentence(text):
    text = clean_text(text)
    sentences = re.split(r'(?<=[.;:])\s+', text)
    for s in sentences:
        if re.search(r'\b(shall|must|required|prohibited|not permitted|only|within)\b', s, re.I) and len(s) > 50:
            return s.strip()
    return sentences[0].strip() if sentences else text[:200]

def first_number(text):
    m = re.search(r'₹\s*[\d,]+(?:/\s*-)?|(\d+)\s*(days?|months?|crore|lakh|per cent|%|\bdays\b)', text)
    return m.group(0).strip() if m else None

# Manual natural-question mapping (written from passage, heading hidden)
MANUAL_QUESTIONS = {
    # factoid (10): write from the first concrete requirement sentence
    0:  None,  # auto
    1:  None,
    2:  None,
    3:  None,
    4:  None,
    5:  None,
    6:  None,
    7:  None,
    8:  None,
    9:  None,
    # table (15)
    10: None,
    11: None,
    # version (10)
    # multi_hop (10)
}

cleaned = []
for i, d in enumerate(drafts):
    cat = d['category']
    text = d.get('source_text', '')
    doc = d.get('doc', '')
    cid = d.get('primary_chunk_id', '')
    cid2 = d.get('secondary_chunk_id', '')

    text_clean = clean_text(text[:600])
    req = first_requirement_sentence(text_clean)
    num = first_number(text_clean)

    if cat == 'factoid':
        # Extract the entity/obligation and form a "what must X do" question
        q = f"What specific obligation or prohibition does the following passage from {doc} impose: '{req[:150]}'?"
        # Simplify by extracting subject
        subj_m = re.search(r'\b(bank|RE|PA|PPI issuer|reporting entity|entity|provider|operator)\b', req, re.I)
        subj = subj_m.group(0) if subj_m else 'an entity'
        q = f"According to {doc}, what must {subj} do regarding: {req[:120].rstrip('.;')}?"

    elif cat == 'table_lookup':
        if num:
            q = f"Under {doc}, what activity is subject to a limit of {num}, and what are the conditions for this limit?"
        else:
            q = f"What operational constraints or thresholds are defined in the following passage from {doc}: '{text_clean[:150]}'?"

    elif cat == 'version_sensitive':
        # Look for a year or circular reference
        yr_m = re.search(r'(RBI/\d{4}-\d{2}/\S+|\d{4})', text_clean)
        yr = yr_m.group(0) if yr_m else 'a prior circular'
        sup_m = re.search(r'(supersede|replac|amend)', text_clean, re.I)
        action = sup_m.group(0).lower() if sup_m else 'update'
        q = f"According to {doc}, which earlier direction or circular does the {yr} provision {action}, and what is the updated requirement?"

    elif cat == 'multi_hop':
        parts = text.split('\n---\n')
        t1 = clean_text(parts[0])[:150] if parts else text_clean[:150]
        t2 = clean_text(parts[1])[:150] if len(parts) > 1 else ''
        docs = doc.split('+')
        d1 = docs[0] if docs else doc
        d2 = docs[1] if len(docs) > 1 else doc
        # Extract shared concept
        kws = ['escrow', 'net-worth', 'authorisation', 'KYC', 'PPI', 'wire transfer', 'beneficial owner']
        shared = next((k for k in kws if k.lower() in text.lower()), 'compliance')
        q = (f"An entity is subject to both {d1} and {d2}. "
             f"What combined obligation arises from their respective {shared} requirements?")
    else:
        q = d['question']

    row = {
        'question': q,
        'category': cat,
        'primary_chunk_id': cid,
        'doc': doc,
        'source_text_preview': text_clean[:300],
        'status': 'DRAFT_NEEDS_REVIEW',
    }
    if cid2:
        row['secondary_chunk_id'] = cid2
    cleaned.append(row)

with open('evals/golden/new_questions_clean.jsonl', 'w', encoding='utf-8') as f:
    for r in cleaned:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')

print(f'Wrote {len(cleaned)} cleaned drafts')
print('\nSample (first of each category):')
seen = set()
for r in cleaned:
    if r['category'] not in seen:
        seen.add(r['category'])
        print(f"\n[{r['category']}] chunk={r['primary_chunk_id']} doc={r['doc']}")
        print(f"  Q: {r['question'][:200]}")
        print(f"  Passage: {r['source_text_preview'][:150]}")
