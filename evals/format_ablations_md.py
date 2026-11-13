import json
from pathlib import Path

data = json.load(open('evals/results/ablations_lean.json', encoding='utf-8'))
lines = [
    '# Multi-Level Retrieval Ablations (95 Clean Dev Questions)',
    '',
    'Evaluated on the frozen dev split (n=95 answerable) with heading-leakage eliminated.',
    'Wilson 95% confidence intervals reported for the primary metric (Recall@5).',
    '',
    '| Configuration | R@5 (Chunk) | 95% Wilson CI | Sec@5 | Doc@5 | Span@5 | R@20 | MRR |',
    '|---|---:|:---:|---:|---:|---:|---:|---:|',
]
for r in data:
    ci = r.get('recall@5_ci95', [0, 0])
    lines.append(
        f"| {r['configuration']} | {r['recall@5']:.4f} | [{ci[0]:.3f}, {ci[1]:.3f}] | {r['section_recall@5']:.4f} | {r['doc_recall@5']:.4f} | {r['span_recall@5']:.4f} | {r['recall@20']:.4f} | {r['mrr']:.4f} |"
    )

lines.append('')
lines.append('### Category Breakdown (Recall@5)')
lines.append('| Configuration | factoid (35) | multi_hop (21) | table_lookup (21) | version_sensitive (18) |')
lines.append('|---|---:|---:|---:|---:|')
for r in data:
    bc = r.get('by_category_recall@5', {})
    lines.append(f"| {r['configuration']} | {bc.get('factoid', 0):.4f} | {bc.get('multi_hop', 0):.4f} | {bc.get('table_lookup', 0):.4f} | {bc.get('version_sensitive', 0):.4f} |")

Path('evals/results/ablations.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
print('Successfully wrote evals/results/ablations.md')
