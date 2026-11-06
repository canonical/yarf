# Preface

Covers YARF's public documentation and the documentation a pull request must
update. Read this before changing a user-visible behavior, command, keyword,
platform plugin, configuration format, or Snap behavior.

Read the top-level `.kb/agents.md` file before continuing below.

# Overview

The public YARF documentation is the Sphinx and MyST site under `docs/`.
`README.md` introduces the project. `CONTRIBUTING.md` and
`docs/CONTRIBUTING.md` explain how contributors build, test, package, and
document YARF. `AGENTS.md` and `.kb/` files are contributor guidance, not
product documentation.

# Important

## Documentation required by a change

Update the relevant documentation in the same pull request when a change
alters a user-visible command, Robot Framework keyword, platform plugin,
configuration value, output format, installation or setup step, supported
platform, Snap behavior, or compatibility guarantee.

A pull request description names the documentation updated. When a change has
no user-visible documentation effect, state that plainly. Do not add public
documentation that repeats internal implementation detail without helping a
user complete a task or understand an interface.

## Location and scope

- Use `docs/` for user and operator documentation published on Read the Docs.
- Use `README.md` for a short project introduction and links to detailed
  documentation.
- Use `CONTRIBUTING.md` for repository-wide development, test, and packaging
  instructions.
- Use `docs/CONTRIBUTING.md` for documentation build and quality-check details.
- Use `AGENTS.md` and `.kb/` only for agent and contributor guidance.

Keep commands, examples, generated library references, and documented behavior
consistent with their implementation. Update generated library documentation
from its source rather than editing generated output by hand.

## Validation and maintenance

Read `docs/AGENTS.md` and `docs/CONTRIBUTING.md` before editing the site. Run
the relevant build and quality checks. These include `make html`, spelling,
link, inclusive-language, Markdown, style, and accessibility checks when the
change can affect them.

Add accepted project terms to `docs/.custom_wordlist.txt`. Preserve links when
moving a published page by adding a redirect in `docs/conf.py` where needed.
Do not publish credentials, private endpoints, or other confidential data.
