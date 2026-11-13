# Week 9 tracing and answer evaluation

`/v1/ask` now returns a trace containing latency for input guard, rewrite,
retrieval, assembly, and generation. Generation also reports its output token
count; cost is zero until a paid provider is configured.

Run the full answer report with:

```text
make eval-answers
```

The report is written to `evals/results/answers.json` and covers all 120 records.
The completed run reports schema validity 1.0, faithfulness 0.5919, correctness
0.2927, refusal accuracy 0.8667, citation accuracy 0.7583, and failure counts
`none=29`, `incorrect=46`, `ungrounded=45`.

Calibration is generated with:

```text
python -m evals.calibrate
```

Its output is `evals/results/calibration.json`. The answer CI gate remains disabled
until the 30 calibration labels are independently confirmed; corpus-grounding
review alone is not sufficient evidence of judge agreement.
