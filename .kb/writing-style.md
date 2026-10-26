# Preface

Defines writing rules for repository documentation, `AGENTS.md` files, pull
request titles and descriptions, review comments, commit messages, and agent
replies. Pull request structure is defined in `.kb/pull-requests.md`.

Read the top-level `.kb/agents.md` file before continuing below.

# Overview

Clear writing states the changed behavior, who it affects, and how it was
verified. The public documentation under `docs/` also follows the Canonical
Documentation Style Guide used by the Sphinx starter pack.

# Important

## Plain language

- State the fact directly. Name the component, command, keyword, or interface.
- Prefer common words and define an abbreviation on first use unless its
  audience already knows it.
- Use American English in contributor guidance.
- Put exact commands, paths, identifiers, and values in backticks.
- Do not expose credentials, private endpoints, or other confidential data.

## Sentences and lists

- Start with the finding, decision, or changed behavior.
- Use complete sentences and state a fact once.
- Use lists for steps, requirements, changed interfaces, and verification.
- Do not use semicolons or em dashes in prose.
- Preserve the spelling and terminology of a public interface or upstream
  system.

## Claims and verification

- Check a behavior claim against code, tests, or the documented contract.
- State commands, checks, and manual steps that were run and their result.
- State relevant verification that was not run and why.
- Describe an intention as an intention, not as implemented behavior.

## Pull requests and reviews

- Begin pull request titles with the required traceability tag. See
  `.kb/pull-requests.md`.
- Start a pull request description with the problem, change, and scope. Follow
  it with review-relevant behavior, compatibility, documentation, and
  verification details. Do not narrate the diff line by line.
- Write an outcome on each review thread. Name the fixing commit or give the
  reason for retaining the current approach.
- Do not add AI or tool attribution to commits, pull requests, comments, or
  documentation.
