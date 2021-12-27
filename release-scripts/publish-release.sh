#!/usr/bin/env bash

SCRIPTS_HOME=$(dirname $0)

function help {
    echo "Usage: $0"
}

source $SCRIPTS_HOME/check-prereqs.sh

version_target=$(poetry version --short)

echo "Creating git tag for release"
git tag --sign --message="Release $version_target" $version_target


echo "Pushing tag to origin"
git push origin $version_target


echo "Publishing to pypicloud"
poetry publish --build --repository=pypicloud


echo "Release process complete!"
