# Preface

This repository follows conventions for organizing agent-oriented knowledge
documents. Read this document before reading or writing an `AGENTS.md` file or
a `.kb/*.md` file.

Read the top-level `.kb/agents.md` file before continuing below.

# Overview

Each directory can provide an `AGENTS.md` file and a `.kb/` directory.
`AGENTS.md` gives a concise guide to the directory. `.kb/*.md` files hold the
detailed, reusable instructions that do not belong in code or user
documentation.

The knowledge base is mechanical, concise, hierarchical, and readable by both
contributors and agents.

# Important

- Read the nearest applicable `AGENTS.md` before working in a directory.
- Keep an `AGENTS.md` or `.kb/*.md` file current when its guidance changes.
- Do not edit this top-level `.kb/agents.md` file unless the change explicitly
  requires it.
- Use dashed lowercase names for `.kb/*.md` files.
- Do not add task logs, plans, or transient investigation notes to `.kb/`.

# Headers

The only top-level headings allowed in `.kb/*.md` files are, in this order:

- _Preface_ - Scope and relevance. It ends with the required sentence that
  directs readers to this file.
- _Overview_ - High-level context, not a file listing.
- _Important_ - Directives and constraints.
- _Headers_ - This registry, only in the top-level `.kb/agents.md`.
- _Architecture_ - Structural boundaries and design decisions.
- _Directory_ - Only in `AGENTS.md` files, a concise directory outline.
- _Documents_ - Only in `AGENTS.md` files, a list of relevant `.kb/*.md` and
  child `AGENTS.md` files. It is the final section.

Use a dashed list in _Directory_ and _Documents_ with the path in backticks,
followed by a concise description.
