"""Print the 9 questions flagged for hand-check."""
import json

rows = [json.loads(l) for l in open('evals/golden/golden.jsonl', encoding='utf-8')]
flagged = [r for r in rows if r.get('hand_check_required')]
print(f'Hand-check flagged: {len(flagged)}\n')
for r in flagged:
    passages = r.get('source_passages', [])
    text = passages[0]['text'][:300] if passages else ''
    print(f"ID: {r['id']} | cat: {r['category']}")
    print(f"Q: {r['question'][:200]}")
    print(f"Passage: {text[:200]}")
    print(f"Ref ans: {str(r.get('reference_answer',''))[:150]}")
    print()
