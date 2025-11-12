#!/usr/bin/env bash
# .github/workflow/scripts/resolve_git_tags.sh
# Resolves FROM/TO tags for a diff range and emits step outputs:
#   from, from_kind (tag|root), to
#
# Inputs (env):
#   IN_FROM
#   IN_TO

set -euo pipefail

# If running outside GitHub Actions, let outputs fall back to stdout
: "${GITHUB_OUTPUT:=}"

emit() {
  local key="$1" val="$2"
  if [[ -n "${GITHUB_OUTPUT}" && -e "${GITHUB_OUTPUT}" ]]; then
    echo "${key}=${val}" >> "${GITHUB_OUTPUT}"
  else
    printf '%s=%s\n' "$key" "$val"
  fi
}

validate_version_format() {
  local version_to_check="$1"
  local version_regex="^[0-9]+\.[0-9]+\.[0-9]+$"

  if [[ ! $version_to_check =~ $version_regex ]]; then
    echo "Error: '$version_to_check' is not in the required <major>.<minor>.<patch> format." >&2
    exit 1
  fi
}


TO_TAG="${IN_TO:-2.0.1}"
validate_version_format "${TO_TAG}"

git fetch --tags --force
git rev-parse -q --verify "refs/tags/${TO_TAG}" >/dev/null || { echo "Tag '${TO_TAG}' not found." >&2; exit 1; }

# Determine FROM_TAG default:
# - Use the previous tag (by creation date) before TO_TAG
# - If there is no previous tag (only one tag exists), mark as ROOT
# Ascending by creation date
mapfile -t TAGS_ASC < <(git for-each-ref --sort=creatordate --format='%(refname:strip=2)' refs/tags)
PREV=""
for i in "${!TAGS_ASC[@]}"; do
  if [[ "${TAGS_ASC[$i]}" == "${TO_TAG}" ]]; then
    if (( i > 0 )); then PREV="${TAGS_ASC[$((i-1))]}"; fi
    validate_version_format "${PREV}"
    break
  fi
done
if [[ -n "${PREV}" ]]; then
  FROM_TAG="${PREV}"
  FROM_KIND="tag"
else
  FROM_TAG=""   # special: repo start
  FROM_KIND="root"
fi

emit "from" "${FROM_TAG}"
emit "from_kind" "${FROM_KIND}"
emit "to" "${TO_TAG}"
