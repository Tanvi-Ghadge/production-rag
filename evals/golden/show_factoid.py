import json

lines = [json.loads(l) for l in open('evals/golden/golden.jsonl')]

# Find all factoid questions and show their source passages for rewriting
factoid_q = [l for l in lines if l.get('category') == 'factoid']
print(f'Total factoid: {len(factoid_q)}')
print('='*80)

# Show first 10 with their gold passage for rewriting
for i, q in enumerate(factoid_q[:10]):
    print(f'\n--- Q{i+1} (id={q.get("id","?")}) ---')
    print(f'ORIGINAL: {q["question"]}')
    print(f'SOURCE_DOC: {q.get("source_doc","?")}')
    # Print first 300 chars of first source passage
    passages = q.get('source_passages', [])
    if passages:
        p = passages[0]
        text = p.get('text', p.get('passage', ''))[:300]
        print(f'GOLD PASSAGE: {text}...')
    print(f'REFERENCE ANSWER: {str(q.get("reference_answer",""))[:200]}')
