#!/usr/bin/env bash
# Check the presence of a single traceability tag in the PR title.
#
# Required environment variables:
#   PR_TITLE, PR_NUMBER, GITHUB_TOKEN, REPO

set -euo pipefail

# Trim leading/trailing whitespace from the PR title and update if necessary
TRIMMED_TITLE=$(printf '%s' "$PR_TITLE" | awk '{$1=$1; print}')
if [ "$TRIMMED_TITLE" != "$PR_TITLE" ]; then
  echo "Updating PR title to: '$TRIMMED_TITLE'"
  PAYLOAD=$(TRIMMED_TITLE="$TRIMMED_TITLE" python3 -c \
    'import json, os; print(json.dumps({"title": os.environ["TRIMMED_TITLE"]}))')
  curl -sS -X PATCH \
    -H "Authorization: Bearer $GITHUB_TOKEN" \
    -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/$REPO/pulls/$PR_NUMBER" \
    -d "$PAYLOAD"
else
  echo "PR title already normalized."
fi

error_msg() {
    title=$(printf '%s' "$TRIMMED_TITLE" | sed -E \
        -e 's/\[[^]]*\]?[[:space:]]*//g' \
        -e 's/(^|[[:space:]])[^[:space:]]*\][[:space:]]*/\1/g' \
        -e 's/\][[:space:]]*//g' \
        -e 's/[[:space:]]+/ /g' \
        -e 's/^[[:space:]]+//; s/[[:space:]]+$//')
    echo "No recognized traceability tag / there are multiple tags"
    echo "Please start the PR title with one of the following tags: [New], [Breaking], [Infra], [BugFix]"
    echo "e.g. [New] $title"
}

if echo "$TRIMMED_TITLE" | grep -Eq '^\[(New|Breaking|Infra|BugFix)\]'; then
    count=$(grep -o '\[[^]]\+\]' <<< "$TRIMMED_TITLE" | wc -l)
    if [ "$count" -eq 1 ]; then
        echo "Traceability tag found."
        exit 0
    else
        error_msg
        exit 1
    fi
else
    error_msg
    exit 1
fi
