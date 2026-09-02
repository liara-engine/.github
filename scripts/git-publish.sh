#!/usr/bin/env bash
#
# Liara Engine — publish a working tree to a shared branch.
#
# Several repositories push generated documentation to the same branch of
# liara-docs. GitHub's `concurrency` keyword cannot serialise them: a
# concurrency group is scoped to a single repository, so two module repos
# using the same group name are still two independent groups. This script
# supplies the missing mutual exclusion the only way a shared git branch
# allows — optimistically, by retrying against the latest remote state.
#
# The retry is safe because concurrent writers touch disjoint paths:
# module A writes site/<A>/..., module B writes site/<B>/.... A rebase of
# one onto the other cannot conflict. Content-addressed files under
# site/_cas/ are the one shared path, and there an identical name implies
# identical bytes, which git resolves as a clean add/add.
#
# Usage:
#   git-publish.sh --repo-dir DIR --branch NAME --message MSG
#                  [--attempts N] [--author-name N] [--author-email E]
#
# Exits 0 when the push succeeded or when there was nothing to commit.
# Exits 1 on a genuine rebase conflict or after exhausting the attempts.

set -Eeuo pipefail

REPO_DIR=""
BRANCH=""
MESSAGE=""
ATTEMPTS=5
AUTHOR_NAME="github-actions[bot]"
AUTHOR_EMAIL="github-actions[bot]@users.noreply.github.com"

die() {
    echo "git-publish: error: $*" >&2
    exit 1
}

usage() {
    sed -n '3,25p' "$0" | sed 's/^# \{0,1\}//'
    exit 2
}

while [ $# -gt 0 ]; do
    case "$1" in
        --repo-dir)     REPO_DIR="${2:-}"; shift 2 ;;
        --branch)       BRANCH="${2:-}"; shift 2 ;;
        --message)      MESSAGE="${2:-}"; shift 2 ;;
        --attempts)     ATTEMPTS="${2:-}"; shift 2 ;;
        --author-name)  AUTHOR_NAME="${2:-}"; shift 2 ;;
        --author-email) AUTHOR_EMAIL="${2:-}"; shift 2 ;;
        -h|--help)      usage ;;
        *)              die "unknown argument: $1" ;;
    esac
done

[ -n "$REPO_DIR" ] || die "--repo-dir is required"
[ -n "$BRANCH" ]   || die "--branch is required"
[ -n "$MESSAGE" ]  || die "--message is required"
[ -d "$REPO_DIR/.git" ] || die "not a git repository: $REPO_DIR"

case "$ATTEMPTS" in
    ''|*[!0-9]*) die "--attempts must be a positive integer" ;;
esac
[ "$ATTEMPTS" -ge 1 ] || die "--attempts must be at least 1"

cd "$REPO_DIR"

git config user.name  "$AUTHOR_NAME"
git config user.email "$AUTHOR_EMAIL"

# Rebasing a merge-free history of generated output needs no merge driver
# cleverness, but an interrupted rebase left behind by a previous step
# would poison the loop below.
if [ -d "$(git rev-parse --git-path rebase-merge)" ] \
    || [ -d "$(git rev-parse --git-path rebase-apply)" ]; then
    die "a rebase is already in progress in $REPO_DIR"
fi

git add -A

if git diff --cached --quiet; then
    echo "git-publish: nothing to commit, working tree matches ${BRANCH}"
    exit 0
fi

git commit --quiet -m "$MESSAGE"
echo "git-publish: committed $(git rev-parse --short HEAD)"

attempt=1
while [ "$attempt" -le "$ATTEMPTS" ]; do
    if git push --quiet origin "HEAD:${BRANCH}" 2>/dev/null; then
        echo "git-publish: pushed to ${BRANCH} on attempt ${attempt}"
        exit 0
    fi

    echo "git-publish: push rejected (attempt ${attempt}/${ATTEMPTS})," \
         "rebasing onto origin/${BRANCH}"

    git fetch --quiet origin "$BRANCH" \
        || die "cannot fetch origin/${BRANCH}"

    if ! git rebase --quiet "origin/${BRANCH}" 2>/dev/null; then
        git rebase --abort >/dev/null 2>&1 || true
        die "rebase conflict against ${BRANCH}." \
            "Concurrent writers are expected to touch disjoint paths;" \
            "a conflict here means that invariant was broken."
    fi

    # Jittered backoff. Without the random term, two racing runners retry
    # in lockstep and keep colliding.
    sleep "$(( attempt * 2 + RANDOM % 4 ))"
    attempt=$(( attempt + 1 ))
done

die "could not push to ${BRANCH} after ${ATTEMPTS} attempts"