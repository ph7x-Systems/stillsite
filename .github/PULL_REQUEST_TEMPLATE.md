## What

<!-- One paragraph: what changes and why. Link the issue: Fixes #NN -->

## Checklist

- [ ] Everything is in English (code, comments, docs, commit messages)
- [ ] Local gates pass: `ruff check . && ruff format --check . && mypy && pytest`
- [ ] Tests added or updated for the change (bug fixes include the regression test)
- [ ] Documentation updated **in this PR** (README/PLAN/ADRs) — the anti-drift
      suite (`tests/test_docs.py`) must stay green; add a check there when this
      PR introduces a new guarded fact
- [ ] Public wiki updated in the same delivery chain, or its external
      synchronization is explicitly recorded as a blocking rollout item
- [ ] No secrets, personal data or client content
- [ ] Architecture decisions recorded as an ADR in `docs/adr/` (if applicable)

By submitting this pull request, I license my contribution under the
repository's [Apache-2.0 license](../LICENSE) (see Section 5 of the license —
no separate CLA is required).
