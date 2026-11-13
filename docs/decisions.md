# Engineering Decisions Log

## D-001 — Winning Configuration Selection Rule (2026-11-13)

**Rule (written before any evaluation run):**

The winning configuration is chosen by **Recall@5 on the dev split**.
Recall@20 is the tiebreaker if two configs are within Wilson 95% CI overlap.
The test split is run **once**, at the very end, on the single selected config.

**Metric levels reported (per config):**
- Strict chunk-level Recall@5 and Recall@20 (primary)
- Section-level Recall@5 (parent_id match)
- Document-level Recall@5
- MRR@10 (chunk level)
All with 95% Wilson confidence intervals.

## D-002 — Question Set Freeze (2026-11-13)

- 40 heading-leaking factoid questions rewritten (see CHANGELOG.md)
- 45 new questions added (10 factoid, 15 table, 10 version, 10 multi_hop)
- 9 of 45 new questions flagged for hand-review
- Stratified 70/30 dev/test split, seed=42, committed to split.json
- Test split LOCKED — do not evaluate on it until final config is chosen
