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

git fetch --tags --force

# Helper: latest tag by creation date
latest_tag() {
  git for-each-ref --sort=-creatordate --format='%(refname:strip=2)' refs/tags | head -n1
}

# Determine TO_TAG default (latest tag if empty)
if [[ -n "${IN_TO:-}" ]]; then
  TO_TAG="${IN_TO}"
else
  TO_TAG="$(latest_tag || true)"
  if [[ -z "${TO_TAG:-}" ]]; then
    echo "No tags found in the repository to use as 'to'." >&2
    exit 1
  fi
fi

git rev-parse -q --verify "refs/tags/${TO_TAG}" >/dev/null || { echo "Tag '${TO_TAG}' not found." >&2; exit 1; }

# Determine FROM_TAG default:
# - If provided, use it (and verify)
# - Else use the previous tag (by creation date) before TO_TAG
# - If there is no previous tag (only one tag exists), mark as ROOT
if [[ -n "${IN_FROM:-}" ]]; then
  FROM_TAG="${IN_FROM}"
  git rev-parse -q --verify "refs/tags/${FROM_TAG}" >/dev/null || { echo "Tag '${FROM_TAG}' not found." >&2; exit 1; }
  FROM_KIND="tag"
else
  # Ascending by creation date
  mapfile -t TAGS_ASC < <(git for-each-ref --sort=creatordate --format='%(refname:strip=2)' refs/tags)
  PREV=""
  for i in "${!TAGS_ASC[@]}"; do
    if [[ "${TAGS_ASC[$i]}" == "${TO_TAG}" ]]; then
      if (( i > 0 )); then PREV="${TAGS_ASC[$((i-1))]}"; fi
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
fi

emit "from" "${FROM_TAG}"
emit "from_kind" "${FROM_KIND}"
emit "to" "${TO_TAG}"
