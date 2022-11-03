#!/usr/bin/env bash

BASE_BRANCH="main"
SUBPROJECT=${PWD##*/}
ALL_SUBPROJECTS="jobbergate-api jobbergate-cli jobbergate-docs"

function bail {
    echo "!!! $1 -- Aborting !!!"
    echo
    help
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

# After this point, abort if commands fail
set -e
