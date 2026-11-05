#!/usr/bin/env bash
# Commit the working-tree changes to the current branch through GitHub's
# createCommitOnBranch API, so the commit is signed and shows as Verified.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

changed=$(git status --porcelain --untracked-files=all | cut -c4-)
if [ -z "$changed" ]; then
  echo "No changes."
  exit 0
fi

# The additions go through a file: a refresh can change enough files that the
# base64 contents exceed the argument-length limit when passed with --argjson.
additions=$(mktemp)
trap 'rm -f "$additions"' EXIT
while IFS= read -r path; do
  jq -n --arg p "$path" --rawfile c <(base64 -w0 "$path") '{path: $p, contents: $c}'
done <<<"$changed" | jq -s . >"$additions"

jq -n \
  --arg repo "$GITHUB_REPOSITORY" \
  --arg branch "$GITHUB_REF_NAME" \
  --arg head "$(git rev-parse HEAD)" \
  --slurpfile additions "$additions" \
  '{query: "mutation($i: CreateCommitOnBranchInput!) { createCommitOnBranch(input: $i) { commit { url } } }",
    variables: {i: {
      branch: {repositoryNameWithOwner: $repo, branchName: $branch},
      expectedHeadOid: $head,
      message: {headline: "docs: refresh articles and live numbers"},
      fileChanges: {additions: $additions[0]}}}}' |
  gh api graphql --input - --jq .data.createCommitOnBranch.commit.url
