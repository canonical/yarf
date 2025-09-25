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

# quick tool checks (non-fatal hints)
command -v gh >/dev/null 2>&1 || { echo "gh CLI not found" >&2; exit 127; }
command -v jq >/dev/null 2>&1 || { echo "jq not found" >&2; exit 127; }

# URL-encode tags for safe API paths
FROM_ESC="$(printf '%s' "${FROM}" | jq -sRr @uri)"
TO_ESC="$(printf '%s' "${TO}" | jq -sRr @uri)"

if [[ "${FROM_KIND}" == "tag" ]]; then
  # Compare API: base...head == FROM..TO
  gh api "repos/${GITHUB_REPOSITORY}/compare/${FROM_ESC}...${TO_ESC}" \
  | jq --arg repo "${GITHUB_REPOSITORY}" '
      .commits
      | map({
          sha: .sha,
          short: (.sha[0:7]),
          url: ("https://github.com/" + $repo + "/commit/" + .sha),
          title: (.commit.message | split("\n")[0]),
          author_login: (.author.login // null),
          author_name:  (.commit.author.name // null),
          committedAt:  .commit.author.date
        })
      | sort_by(.committedAt) | reverse
    ' > commits.json
else
  # Only one tag exists -> gather all commits reachable by TO (paginate)
  : > rows.ndjson
  PAGE=1
  while :; do
    RESP="$(gh api "repos/${GITHUB_REPOSITORY}/commits?sha=${TO_ESC}&per_page=100&page=${PAGE}")"
    COUNT="$(jq 'length' <<<"$RESP")"
    if [[ "$COUNT" -eq 0 ]]; then break; fi
    jq -c --arg repo "${GITHUB_REPOSITORY}" '
      map({
        sha: .sha,
        short: (.sha[0:7]),
        url: ("https://github.com/" + $repo + "/commit/" + .sha),
        title: (.commit.message | split("\n")[0]),
        author_login: (.author.login // null),
        author_name:  (.commit.author.name // null),
        committedAt:  .commit.author.date
      }) | .[]
    ' <<<"$RESP" >> rows.ndjson
    PAGE=$((PAGE+1))
  done

  if [[ -s rows.ndjson ]]; then
    jq -s 'sort_by(.committedAt) | reverse' rows.ndjson > commits.json
  else
    echo "[]" > commits.json
  fi
fi

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
