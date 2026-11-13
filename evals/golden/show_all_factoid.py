import json

lines = [json.loads(l) for l in open('evals/golden/golden.jsonl')]
factoid_q = [l for l in lines if l.get('category') == 'factoid']
print(f'Total factoid: {len(factoid_q)}')
for i, q in enumerate(factoid_q):
    passages = q.get('source_passages', [])
    text = ''
    if passages:
        p = passages[0]
        text = p.get('text', p.get('passage', ''))[:400]
    print(f'\n--- Q{i+1} id={q.get("id")} ---')
    print(f'ORIG: {q["question"]}')
    print(f'PASSAGE: {text}')
    print(f'ANS: {str(q.get("reference_answer",""))[:200]}')
