# Red-team report

- Total suite cases: 59 (Passed: 59, Failed: 0)
- Adversarial attack probes: 45
- Benign queries evaluated: 100

| Stage | Attack Success Rate | False-Positive Rate (Benign) |
|---|---:|---:|
| Before guardrails | 100.00% | 0.00% |
| Legacy single-regex baseline | 62.22% | 0.00% |
| After multi-layer guardrails | 0.00% | 1.00% |

## Limitations

- Second-layer check uses deterministic intent scoring offline unless RAG_LLM_GUARD=1 with a live LLM key.
- Provider failure is tested with a deterministic failing fixture.
- pgvector failure is tested with a deterministic connection fixture.
- Azure and deployed-network red-team behavior requires deployment credentials.
