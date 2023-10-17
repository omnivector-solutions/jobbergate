#!/usr/bin/env bash

SCRIPTS_HOME=$(dirname $0)

function help {
    echo ""
    echo "Usage: $0 VERSION_TYPE"
    echo ""
    echo "  VERSION_TYPE: Type of new version to create. Must be one of:"
    echo "                (major|minor|patch|prerelease|premajor|preminor|prepatch)"
    echo ""
}

source $SCRIPTS_HOME/check-prereqs.sh

version_type=$1
if [[ -z $version_type ]]
then
    bail "No version type specified."
fi

echo "Creating release for version increment in $version_type"

poetry version $version_type
version_target=$(poetry version --short)

echo "Building release $version_target"

echo "Updating CHANGELOG"
version_line="## $version_target -- $(date '+%Y-%m-%d')"
replacement="## Unreleased\n\n\n$version_line\n"
perl -0777 -p -i -e "s/## Unreleased\s*/$replacement/gs" CHANGELOG.md
