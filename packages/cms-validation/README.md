# sardine-cms-validation

The Sardine CMS validation engine: composable, configurable rules that run
before every publish — required translations per language, unique slugs per
language, media references, alt-text coverage, known categories. Errors
block publishing; the same rules power the CLI gate and the admin's publish
gate.

```bash
pip install sardine-cms-validation
```

A rule is any object with a `name` and `check(content, context)`; a
`RuleSet` aggregates issues into a `Report` (`errors`, `warnings`, `ok`).

## Sardine CMS

A multilingual, static-first CMS framework: EN-source content with
checksum-tracked translation states (PT-PT, ES, FR, DE), validation gates
before publishing, deterministic builds with full multilingual SEO, and a
browser admin for the whole editorial cycle.

- Live demo: <https://sardine.ph7x.com> (admin demo at [/admin/](https://sardine.ph7x.com/admin/))
- Repository: <https://github.com/ph7x-Systems/sardine-cms>
- Documentation: <https://github.com/ph7x-Systems/sardine-cms/wiki>
- License: Apache-2.0
