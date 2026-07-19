# cms-cli

The Sardine CMS command line. Reads `sardine.toml` in the project directory
and drives the framework end-to-end:

```bash
cms seed       # create fictional starter content in the project storage
cms validate   # run the validation rules; non-zero exit on errors
cms build      # validate + deterministic build into the output directory
cms export     # build + deployment-target config (--target swa|nginx|generic)
cms preview    # serve the built site locally
```
