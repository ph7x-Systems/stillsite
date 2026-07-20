# Architecture — Layers and Development Rules

Sardine CMS follows a strict layered architecture (ports & adapters). The rules
below are enforceable, not aspirational: dependency direction is checked by
review and tests, contracts are typed `Protocol`s/ABCs, and mypy strict is a
required CI gate. Rationale recorded in [ADR-0006](adr/0006-layered-architecture.md).

## Layers

```text
┌────────────────────────────────────────────────────────┐
│  Interface        cms-cli (Typer), cms-admin           │  thin: parse input,
│                   (FastAPI + server-rendered UI,       │
│                   ADR-0013)                            │
├────────────────────────────────────────────────────────┤  wire config, call
│  Application      cms-validation (rule engine),        │  services, present
│                   cms-build (builder, exporter)        │  results
├────────────────────────────────────────────────────────┤
│  Domain           cms-core: models, translation        │  pure: no I/O, no
│                   states, checksums                    │  clock, no config
├────────────────────────────────────────────────────────┤
│  Adapters         storage backends, deployment         │  plug in via
│  (infrastructure) targets, themes                      │  registries
└────────────────────────────────────────────────────────┘
```

**Dependencies point inward only.** Domain imports nothing above it.
Application imports domain. Interface imports application. Adapters implement
contracts defined by the layer that consumes them (`StorageBackend` in
domain/storage, `Theme` and `Target` in build) and are selected by
configuration, never imported directly by name in application code.

## Extension points (all registry-based, per the extensibility contracts)

| Contract | Registry | Ships with |
| --- | --- | --- |
| `StorageBackend` | `register_backend(scheme, factory)` | sqlite, postgresql, mysql, mssql |
| `Target` (deployment) | `register_target(name, target)` | generic, swa, nginx |
| `Theme` | `register_theme(name, theme)` | default, reference theme package |
| Validation `Rule` | `RuleSet` composition | core rules + extension contributions |
| `Extension` | `sardine.extensions` entry points or dotted paths | explicit activation; rules, build steps, registries, CLI and section hints |

## Development rules

1. **No product hardcoding.** URLs, language lists, site names, output paths
   and feature switches come from `SiteConfig`/project configuration — never
   literals in application code. Editorial text never appears in templates.
   Wire-format identifiers may be constants only inside their explicit
   adapter; they must not cause network access or leak into the domain model.
2. **Contracts first.** Every cross-layer boundary is a typed `Protocol` or
   ABC with a conformance test suite. New adapters pass the suite unchanged.
3. **Pure domain.** `cms-core` performs no I/O, reads no clock (`now` is
   always injected), imports no framework. Anything impure lives in adapters.
4. **Determinism in the build path.** No wall-clock, randomness or dict-order
   dependence between content in and bytes out. Same input → identical bytes;
   a test builds twice and compares hashes.
5. **Fail loudly.** Unknown scheme/target/theme raises with the known options
   listed. No silent fallbacks, no defaults that mask misconfiguration.
6. **Generated, not hand-assembled.** Head contract (canonical, hreflang, OG),
   sitemap, feeds and search indexes are derived from the content model in one
   place. Templates receive them; they never construct them.
7. **Escape by default.** Jinja autoescape everywhere; Markdown rendered with
   raw HTML disabled. Rich content enters only via reviewed constructs.
8. **Typed strict, tested, documented.** mypy strict and ruff pass with zero
   ignores added; every guarantee gets a test (TEST_PLAN.md); docs move in the
   same PR (anti-drift suite).
9. **Small seams.** Functions take the narrowest type that works (an
   `Iterable[Article]`, not a storage backend) so layers stay testable in
   isolation.
