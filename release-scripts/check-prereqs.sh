#!/usr/bin/env bash

BASE_BRANCH="main"
SUBPROJECT=${PWD##*/}
ALL_SUBPROJECTS="jobbergate-api jobbergate-cli"

function bail {
    echo "!!! $1 -- Aborting !!!"
    echo
    help
    echo "  * You must have git configured with a signing key"
    echo "  * You must have the $BASE_BRANCH branch checked out"
    echo "  * You must have no staged changes"
    echo "  * Your $BASE_BRANCH branch must be up-to-date with origin"
    echo "  * You must have no local or remote tags matching the target version"
    echo "  * You must run the script from one of the sub-projects: $ALL_SUBPROJECTS"
    exit 1
}

echo "Checking prerequisites"

echo "Checking if current directory is a releaseable subproject"
if [[ " ${ALL_SUBPROJECTS[@]} " =~ " ${SUBPROJECT} " ]]
then
    echo "$SUBPROJECT is a valid sub-project"
else
    bail "This script must be run from one of the valid sub-projects: $ALL_SUBPROJECTS"
fi

echo "Checking for $BASE_BRANCH branch"
current_branch=$(git rev-parse --abbrev-ref HEAD)
if [[ "$current_branch" != "$BASE_BRANCH" ]]
then
    bail "Must be on $BASE_BRANCH branch. Current branch is $current_branch"
fi


echo "Checking for staged changes"
staged_changes=$(git diff --name-only --cached | tr -d '[:space:]')
if [[ -n $staged_changes ]]
then
    bail "You have the changes staged for the following files:\n$staged_changes"
fi


echo "Making sure $BASE_BRANCH is up-to-date with origin"
git fetch
git status | grep "Your branch is up to date with 'origin/$BASE_BRANCH'"
if (( $? ))
then
    bail "Your branch is not up to date with origin"
fi


echo "Checking signing key"
key_id=$(git config user.signingkey)
if [[ -z $key_id ]]
then
    bail "You must have git configured with a signing key."
fi


echo "Making sure the signing key may be used"
gpg --dry-run --sign --local-user $key_id $(pwd)/$0
if (( $? ))
then
    bail "Couldn't sign with configured key."
fi

# After this point, abort if commands fail
set -e
