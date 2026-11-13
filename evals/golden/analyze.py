import json

lines = [json.loads(l) for l in open('evals/golden/golden.jsonl')]
cats = {}
for l in lines:
    c = l.get('category', 'unknown')
    cats[c] = cats.get(c, 0) + 1

print('Total:', len(lines))
print('By category:', json.dumps(cats, indent=2))

# Find heading-quoting questions
heading_q = [l for l in lines if "stated in '" in l.get('question', '') or 
             ("what requirement" in l.get('question', '').lower() and "'" in l.get('question', ''))]
print('Heading-quoting (stated in pattern):', len(heading_q))

# Check factoid category
factoid_q = [l for l in lines if l.get('category') == 'factoid']
print('Factoid total:', len(factoid_q))
print('\nFirst 3 factoid questions:')
for q in factoid_q[:3]:
    print(' -', q['question'][:120])
