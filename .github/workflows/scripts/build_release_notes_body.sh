#!/usr/bin/env bash
# .github/workflow/scripts/build-release-notes.sh
# Builds a Markdown release body from commits.json produced earlier.
# Requires: jq
#
# Inputs (env):
#   FROM_KIND  - "tag" or "root" (from resolve-tags step)
#   FROM       - tag name when FROM_KIND=tag (may be empty when root)
#   TO         - target tag name (release tag)
#   COMMITS_PATH - optional, path to commits JSON (default: commits.json)
#   OUTPUT_PATH  - optional, path to write release body (default: release_body.md)
#
# Step outputs:
#   note_from - formatted "from" text used in the header
#   path      - path to the generated Markdown file

set -euo pipefail

: "${GITHUB_OUTPUT:=}"
: "${FROM_KIND:?FROM_KIND is required (tag|root)}"
: "${TO:?TO tag is required}"
: "${FROM:=}"
COMMITS_PATH="${COMMITS_PATH:-commits.json}"
OUTPUT_PATH="${OUTPUT_PATH:-release_body.md}"

command -v jq >/dev/null 2>&1 || { echo "jq is required" >&2; exit 127; }
[[ -f "$COMMITS_PATH" ]] || { echo "Missing $COMMITS_PATH" >&2; exit 1; }

# Build categorized sections from commits.json
jq -r '
  def has_prefix:
    (.title | test("^\\[(Breaking|New|BugFix|Infra)\\]"; "i"));
  def category:
    if (.title|test("^\\[Breaking\\]";"i")) then "Breaking"
    elif (.title|test("^\\[New\\]";"i")) then "New"
    elif (.title|test("^\\[BugFix\\]";"i")) then "BugFix"
    elif (.title|test("^\\[Infra\\]";"i")) then "Infra"
    else null end;
  def clean_title:
    .title | sub("^\\[(Breaking|New|BugFix|Infra)\\]\\s*"; "");
  def author:
    if .author_login then "@" + .author_login
    elif .author_name then .author_name
    else "unknown" end;
  def line:
    "- [" + (clean_title) + "](" + .url + ") by " + (author);

  . as $all
  | def section($label; $key):
      ([$all[] | select(category == $key) | line]) as $lines
      | if ($lines|length) > 0
        then "\n### " + $label + "\n" + ($lines | join("\n"))
        else "" end;

  "## Changes"
  + section("Breaking Changes"; "Breaking")
  + section("New";               "New")
  + section("Bug Fixes";         "BugFix")
  + section("Infrastructure";    "Infra")
' "$COMMITS_PATH" > sections.md

if [[ "${FROM_KIND}" == "tag" ]]; then
  NOTE_FROM="\`${FROM}\`"
else
  NOTE_FROM="repository start"
fi

{
  echo "# Release ${TO}"
  echo
  echo "> Changes merged after ${NOTE_FROM} and up to and including \`${TO}\`."
  echo
  cat sections.md
} > "${OUTPUT_PATH}"

# Emit step outputs if available
if [[ -n "${GITHUB_OUTPUT}" && -e "${GITHUB_OUTPUT}" ]]; then
  {
    echo "note_from=${NOTE_FROM}"
    echo "path=${OUTPUT_PATH}"
  } >> "${GITHUB_OUTPUT}"
fi

# Helpful log
cat "${OUTPUT_PATH}"
