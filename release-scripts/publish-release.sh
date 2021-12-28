#!/usr/bin/env bash

SCRIPTS_HOME=$(dirname $0)

function help {
    echo "Usage: $0"
}

source $SCRIPTS_HOME/check-prereqs.sh

version_target=$(poetry version --short)

tag_name="$SUBPROJECT-$version_target"
echo "Creating git tag $tag_name for release"
git tag --sign --message="Release $tag_name" $tag_name


echo "Pushing tag to origin"
git push origin $tag_name


echo "Publishing to pypicloud"
poetry publish --build --repository=pypicloud


echo "Release process complete!"
