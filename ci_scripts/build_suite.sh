#!/bin/bash
#
# Build  script for g3w-suite, to be run inside the docker container
#
# Depending on the existence of "build_done" file
# setup steps are performed, they consist in:
# - js build with yarn

set -e

CODE_DIRECTORY='/code'
DATASOURCE_PATH='/shared-volume/project_data'
MEDIA_ROOT='/shared-volume/media'
PROJECTS_DIR="${MEDIA_ROOT}/projects"
BUILD_DONE_FILE='/code/build_done'
DJANGO_DIRECTORY="${CODE_DIRECTORY}/g3w-admin"

cd '/code/'


if [ ! -e ${BUILD_DONE_FILE} ]; then
    echo "Build started for G3W-Suite installation ..."

    echo "Building javascript code ..."
    yarn --ignore-engines --ignore-scripts --prod
    nodejs -e "try { require('fs').symlinkSync(require('path').resolve('node_modules/@bower_components'), 'g3w-admin/core/static/bower_components', 'junction') } catch (e) { }"

else
    echo "Build was already done, skipping ..."
    # Wait for postgis
    wait-for-it -h postgis -p 5432 -t 60
fi

# Make sure data are readable:
chmod -R 777 ${DATASOURCE_PATH}
