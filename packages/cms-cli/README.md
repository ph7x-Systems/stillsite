# sardine-cms-cli

The Sardine CMS command line. Reads `sardine.toml` in the project directory
and drives the framework end-to-end:

```bash
pip install sardine-cms-cli

cms init my-site --name "My Site" --base-url "https://my-site.example"
cms seed       # fictional starter content, five languages
cms validate   # the rules; non-zero exit on errors
cms build      # validate + deterministic build into the output directory
cms export     # build + deployment-target config (--target swa|nginx|generic|astro)
cms preview    # serve the built site locally
cms dump       # portable content.json + Markdown backup
cms import portable                  # restore a portable dump
cms import --help                         # list native and external input formats
cms admin create-user <name> --role admin   # first admin account (no defaults)
```

## Sardine CMS

A multilingual, static-first CMS framework: EN-source content with
checksum-tracked translation states (PT-PT, ES, FR, DE), validation gates
before publishing, deterministic builds with full multilingual SEO, and a
browser admin for the whole editorial cycle.

- Live demo: <https://sardine.ph7x.com> (admin demo at [/admin/](https://sardine.ph7x.com/admin/))
- Repository: <https://github.com/ph7x-Systems/sardine-cms>
- Documentation: <https://github.com/ph7x-Systems/sardine-cms/wiki>
- License: Apache-2.0
