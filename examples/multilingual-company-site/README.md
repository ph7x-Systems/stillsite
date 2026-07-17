# Example: multilingual company site

A fictional company ("Aurora Cartography") in five languages, driven entirely
by the framework. Everything here is invented content.

```bash
cms seed     -p examples/multilingual-company-site   # starter content (SQLite)
cms validate -p examples/multilingual-company-site
cms build    -p examples/multilingual-company-site   # deterministic _site/
cms export   -p examples/multilingual-company-site --target swa
cms preview  -p examples/multilingual-company-site
```

The generated `content.sqlite3` and `_site/` are build artifacts and are not
committed.
