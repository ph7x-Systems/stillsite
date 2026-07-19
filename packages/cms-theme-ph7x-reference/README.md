# cms-theme-ph7x-reference

The Sardine CMS reference theme: a dark editorial design system — token-driven,
local Inter/Newsreader fonts (OFL, shipped alongside), CSS-only effects that
honor reduced motion, zero inline styles, no external requests.

```toml
# sardine.toml
[site]
theme = "ph7x-reference"
```

Installed as a package, discovered via the `sardine.themes` entry point
(ADR-0012); it layers over the default theme's templates, so it only ships
what it changes. Conformance: docs/DESIGN_RULES.md, tested by the theme
conformance suite.
