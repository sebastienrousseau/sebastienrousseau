#!/usr/bin/env bash
# Keep one issue in step with the refresh: open or comment on it when a
# run fails, close it when a run succeeds. A red scheduled run alone went
# unnoticed for 23 days; an open issue does not.
#
#   tools/alert.sh fail | ok
#
# Needs GH_TOKEN with issues: write, plus GITHUB_REPOSITORY,
# GITHUB_SERVER_URL and GITHUB_RUN_ID (all set in Actions).
set -euo pipefail

title="refresh: profile data is stale"
run="$GITHUB_SERVER_URL/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID"
open=$(gh issue list --repo "$GITHUB_REPOSITORY" --state open --search "in:title \"$title\"" \
  --json number,title --jq "map(select(.title == \"$title\")) | .[0].number // empty")

case ${1:-} in
  fail)
    if [ -n "$open" ]; then
      gh issue comment "$open" --repo "$GITHUB_REPOSITORY" --body "Still failing: $run"
    else
      gh issue create --repo "$GITHUB_REPOSITORY" --title "$title" --body \
        "The profile refresh failed. The profile keeps its last good numbers; see the run summary for which source is stuck and since when: $run"
    fi
    ;;
  ok)
    if [ -n "$open" ]; then
      gh issue close "$open" --repo "$GITHUB_REPOSITORY" --comment "Recovered: $run"
    fi
    ;;
  *)
    echo "usage: $0 fail | ok" >&2
    exit 2
    ;;
esac
