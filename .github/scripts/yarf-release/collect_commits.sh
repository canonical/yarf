#!/usr/bin/env bash
# .github/workflow/scripts/collect_commits.sh
# Requires: gh, jq; uses GH_TOKEN for auth
# Inputs (env): FROM_KIND, FROM, TO, GITHUB_REPOSITORY
# Outputs (file): commits.json
# Step outputs: commits_path, commit_count

set -euo pipefail

: "${GITHUB_OUTPUT:=}"
: "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"
: "${TO:?TO tag is required}"
: "${FROM_KIND:?FROM_KIND is required (tag|root)}"
: "${FROM:=}"  # may be empty when FROM_KIND=root

command -v jq >/dev/null 2>&1 || { echo "jq not found" >&2; exit 127; }

# URL-encode tags for safe API paths
FROM_ESC="$(printf '%s' "${FROM}" | jq -sRr @uri)"
TO_ESC="$(printf '%s' "${TO}" | jq -sRr @uri)"

if [[ "${FROM_KIND}" == "tag" ]]; then
  # We have a start and end tag
  GIT_RANGE="${FROM}..${TO}"
else
  # We only have an end tag
  GIT_RANGE="${TO}"
fi

git log "${GIT_RANGE}" \
  --pretty=format:'%H|%h|%s|%an|%aI' |
awk -v repo="${GITHUB_REPOSITORY}" -F '|' '
function tojson(str) {
  gsub(/"/, "\\\"", str)
  return "\"" str "\""
}
{
  printf("{\"sha\": %s, \"short\": %s, \"url\": %s, \"title\": %s, \"author_name\": %s, \"committedAt\": %s}\n",
    tojson($1),
    tojson($2),
    tojson("https://github.com/" repo "/commit/" $1),
    tojson($3),
    tojson($4),
    tojson($5))
}' | jq -s '.' > commits.json

# Ensure non-empty file
if [[ ! -s commits.json ]]; then echo "[]" > commits.json; fi

# Emit step outputs for downstream steps
COUNT="$(jq 'length' commits.json)"
if [[ -n "${GITHUB_OUTPUT}" && -e "${GITHUB_OUTPUT}" ]]; then
  {
    echo "commits_path=commits.json"
    echo "commit_count=${COUNT}"
  } >> "${GITHUB_OUTPUT}"
fi

echo "Wrote commits.json (${COUNT} commits)"
