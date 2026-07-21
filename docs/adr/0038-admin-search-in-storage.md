# ADR-0038 — Admin search lives in the storage contract

- **Status:** accepted
- **Date:** 2026-07-21

## Context

Global admin search (#129) must answer in under 300 ms on a
10 000-entry database. Loading every entry and filtering in Python
cannot meet that: `load_all_articles` issues per-entry translation
queries. The only layer that can search efficiently is the one that
owns the SQL — which makes this a storage-contract decision, hence an
ADR despite its small size.

## Decision

`StorageBackend` gains one additive method:

```python
def search_content(self, needle: str, limit: int = 20) -> list[SearchHit]
```

- `SearchHit` (`cms_core.search`) is deliberately tiny: kind, id,
  title, detail — a result row for the admin, not an API.
- The **base class ships a portable default** that walks loaded
  content: third-party backends inherit correctness for free and may
  override for speed.
- The bundled engines override with four LIKE queries (articles,
  pages+translations, sections incl. items JSON, media incl. alt
  texts), case-folded on both sides, user input made literal with
  `ESCAPE '!'` (a backslash would itself need escaping on MySQL).
- No index tables, no external search engine: LIKE over the working
  store meets the budget with an order of magnitude to spare
  (measured: worst case 13.6 ms SQLite, 34.5 ms PostgreSQL at 10 000
  entries — `scripts/search_bench.py` is the method and the proof).
- Trashed entries never match: search finds what the lists show.

## Consequences

- The conformance suite covers the method on all four engines;
  third-party backends get the test for free by running it.
- If a future site outgrows LIKE (full-text ranking, fuzziness), that
  is a new decision — this contract stays the interface.
