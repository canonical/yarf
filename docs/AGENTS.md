# Preface

Instructions for the user-facing YARF documentation in this directory. The
site uses Sphinx and MyST through Canonical's documentation starter pack.

Read the top-level `.kb/agents.md` file before continuing below.

# Overview

The documentation explains how to install, configure, and use YARF. It
includes tutorials, how-to guides, reference material, and explanation. Robot
Framework library reference pages are generated from source library
documentation.

# Important

Read [`../.kb/writing-style.md`](../.kb/writing-style.md) and
[`../.kb/documentation.md`](../.kb/documentation.md) before changing this
directory. Read [`CONTRIBUTING.md`](CONTRIBUTING.md) for the complete build and
quality-check instructions.

Build and check documentation from this directory:

```bash
make install
make html
make spelling
make linkcheck
make woke
make vale
make pa11y
```

Run the checks relevant to the change. Add accepted project terms to
`.custom_wordlist.txt`, rather than changing a correct term to satisfy a
spelling check.

Do not hand-edit generated Robot library reference pages. Change the source
library documentation, then run `make libdoc-convert`.

# Directory

- `tutorial/` - Guided learning material.
- `how-to/` - Task-oriented procedures.
- `reference/` - Stable command, metadata, and Robot library reference.
- `explanation/` - Background and design concepts.

# Documents

- `../.kb/documentation.md` - Repository-wide documentation scope and maintenance.
- `../.kb/writing-style.md` - Repository writing rules.
- `CONTRIBUTING.md` - Documentation builds and quality checks.
