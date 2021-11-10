#!/usr/bin/env bash

function help {
    echo ""
    echo "Usage: $0 VERSION_TYPE"
    echo
    echo "  VERSION_TYPE: Type of new version to create. Must be one of:"
    echo "                (major|minor|patch|prerelease|premajor|preminor|prepatch)"
    echo""
    echo "  * You must have git configured with a signing key"
    echo "  * You must have the main branch checked out"
    echo "  * You must have no staged changes"
    echo "  * Your main branch must be up-to-date with origin"
    exit 1
}

function bail {
    echo "!!! $1 -- Aborting !!!"
    echo
    help
}


version_type=$1
if [[ -z $version_type ]]
then
    echo "No version type specified."
    help
fi

echo "Checking prerequisites"

echo "Checking for main branch"
current_branch=$(git rev-parse --abbrev-ref HEAD)
if [[ $current_branch -ne "main" ]]
then
    bail "Must be on main branch. Current branch is $current_branch"
fi


echo "Checking for staged changes"
staged_changes=$(git diff --name-only --cached | tr -d '[:space:]')
if [[ -n $staged_changes ]]
then
    bail "You have the changes staged for the following files:\n$staged_changes"
fi


echo "Making sure main is up-to-date with origin"
git fetch
git status | grep "Your branch is up to date with 'origin/main'"
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


echo "Creating release for version increment in $version_type"

# After this point, abort if commands fail
set -e

poetry version $version_type
version_target=$(poetry version --short)

echo "Building release $version_target"

echo "Updating CHANGELOG"
version_line="$version_target -- $(date '+%Y-%m-%d')"
replacement='Unreleased\n$1\n\n'
replacement+="$version_line\n"
replacement+="$(printf %${#version_line}s | tr ' ' '-')"
perl -0777 -p -i -e "s/Unreleased\s*(-+)/$replacement/gs" CHANGELOG.rst


echo "Creating commit for release"
git add pyproject.toml CHANGELOG.rst
git commit --gpg-sign --message="Created release $version_target"


echo "Creating git tag for release"
git tag --sign --message="Release $version_target" $version_target


echo "Pushing commit and tag to origin"
git push origin $version_target main


echo "Publishing to pypicloud"
poetry publish --build --repository=pypicloud


echo "Release process complete!"
