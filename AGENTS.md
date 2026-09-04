# Repository working memory

For work involving `temp/`, read `docs/temp-v2-workflow.md` and `docs/temp-v2-status.md` first. Treat `data/exams.csv` as the only source of truth and `temp/` as read-only candidate material.

Do not load the whole temp collection, a full audit CSV, or many PDFs into conversation context. Select candidates from the reports, inspect only the relevant rows and representative pages, and keep render scratch files under ignored `tmp/pdfs/`.

Use the deterministic stratified sample from `scripts/sample_temp_v2_review.py`; inspect first/middle/last pages only. If one sample fails, expand that action-and-subject stratum to full review. Run `scripts/clean_temp_v2_cache.py --apply` at the end of every review batch.

Never replace a `verified` record merely because names, page counts, or extracted text look similar. Every mutation must be an explicit hash-locked decision in `scripts/apply_temp_v2_replacements.py`, followed by the audit, status, catalog checks, and tests documented in the workflow.
