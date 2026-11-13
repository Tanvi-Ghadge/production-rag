# Multi-Level Retrieval Ablations (95 Clean Dev Questions)

Evaluated on the frozen dev split (n=95 answerable) with heading-leakage eliminated.
Wilson 95% confidence intervals reported for the primary metric (Recall@5).

| Configuration | R@5 (Chunk) | 95% Wilson CI | Sec@5 | Doc@5 | Span@5 | R@20 | MRR |
|---|---:|:---:|---:|---:|---:|---:|---:|
| bm25:400:0 | 0.6632 | [0.563, 0.750] | 0.6632 | 0.9158 | 0.6526 | 0.7579 | 0.5704 |
| dense:400:0 | 0.5053 | [0.406, 0.604] | 0.5053 | 0.8105 | 0.5263 | 0.5895 | 0.3932 |
| hybrid (baseline) | 0.6211 | [0.521, 0.712] | 0.6211 | 0.8947 | 0.6526 | 0.6947 | 0.4611 |
| +identifier_boost | 0.6526 | [0.553, 0.741] | 0.6526 | 0.9474 | 0.6842 | 0.7789 | 0.5259 |
| hybrid +rerank top20->10 | 0.6000 | [0.499, 0.693] | 0.6000 | 0.8842 | 0.6316 | 0.6316 | 0.4507 |
| hybrid +rerank top50->10 | 0.5895 | [0.489, 0.683] | 0.5895 | 0.9368 | 0.6316 | 0.6211 | 0.4393 |
| +id_boost +rerank top50->10 | 0.6105 | [0.510, 0.703] | 0.6105 | 0.9579 | 0.6526 | 0.6632 | 0.4586 |
| +ctx_headers | 0.6421 | [0.542, 0.731] | 0.6421 | 0.9053 | 0.6316 | 0.7263 | 0.5122 |
| +ctx_headers +rerank top50->10 | 0.7474 | [0.652, 0.824] | 0.7474 | 0.9789 | 0.7368 | 0.7684 | 0.6575 |

### Category Breakdown (Recall@5)
| Configuration | factoid (35) | multi_hop (21) | table_lookup (21) | version_sensitive (18) |
|---|---:|---:|---:|---:|
| bm25:400:0 | 0.7714 | 0.5714 | 0.8095 | 0.3889 |
| dense:400:0 | 0.6857 | 0.1905 | 0.6190 | 0.3889 |
| hybrid (baseline) | 0.8286 | 0.3810 | 0.6667 | 0.4444 |
| +identifier_boost | 0.8286 | 0.4286 | 0.7619 | 0.4444 |
| hybrid +rerank top20->10 | 0.8000 | 0.4286 | 0.5714 | 0.4444 |
| hybrid +rerank top50->10 | 0.8286 | 0.3810 | 0.6667 | 0.2778 |
| +id_boost +rerank top50->10 | 0.8286 | 0.4286 | 0.7143 | 0.2778 |
| +ctx_headers | 0.8571 | 0.5238 | 0.6190 | 0.3889 |
| +ctx_headers +rerank top50->10 | 0.9143 | 0.6190 | 0.8095 | 0.5000 |
