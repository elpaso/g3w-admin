#!/bin/bash
#
# Biuld  script for g3w-suite, to be run inside the docker container
#
# Depending on the existence of "setup_done" file
# setup steps are performed, they consist in:
# - js build with yarn
# - media and static re-creation from empty directories
# - Django setup
#   - migrations
#   - collect static
#   - admin user and fake passwords
#   - fixtures installation

set -e

CODE_DIRECTORY='/code'
DATASOURCE_PATH='/shared-volume/project_data'
MEDIA_ROOT='/shared-volume/media'
PROJECTS_DIR="${MEDIA_ROOT}/projects"
SETUP_DONE_FILE='/code/setup_done'
DJANGO_DIRECTORY="${CODE_DIRECTORY}/g3w-admin"

cd '/code/'


if [ ! -e ${SETUP_DONE_FILE} ]; then
    echo "Setup started for G3W-Suite installation ..."
    echo "Copying docker_settings.py to base/settings/local_settings.py"
    cp ./settings_docker.py ./g3w-admin/base/settings/local_settings.py

    echo "Building javascript code ..."
    yarn --ignore-engines --ignore-scripts --prod
    nodejs -e "try { require('fs').symlinkSync(require('path').resolve('node_modules/@bower_components'), 'g3w-admin/core/static/bower_components', 'junction') } catch (e) { }"

    echo "Cleaning up some dirs before collecting statics ..."
    ls ${MEDIA_ROOT} || mkdir ${MEDIA_ROOT}
    pushd .
    cd ${MEDIA_ROOT}/..
    ls static || ln -s media static
    popd

    echo "Creating projects(_data) directores in ${PROJECTS_DIR} ..."
    ls ${PROJECTS_DIR} || mkdir ${PROJECTS_DIR}
    ls ${DATASOURCE_PATH} || mkdir ${DATASOURCE_PATH}

    pushd .
    cd ${DJANGO_DIRECTORY}/core/static
    rm -rf bower_components
    ln -s "/code/node_modules/@bower_components" bower_components
    popd

    # Wait for postgis here so we avoid waiting while building js code
    wait-for-it -h postgis -p 5432 -t 60

    cd ${DJANGO_DIRECTORY}
    python manage.py collectstatic --noinput -v 0
    python manage.py migrate --noinput

    echo "Installing fixtures ..."
    for FIXTURE in 'BaseLayer.json' 'G3WGeneralDataSuite.json' 'G3WMapControls.json' 'G3WSpatialRefSys.json'; do
        python manage.py loaddata  core/fixtures/${FIXTURE}
    done
    # sync menu tree items
    python manage.py sitetree_resync_apps
    python manage.py createsuperuser --noinput --username admin --email admin@email.com || true
    # Fails if not debug
    python manage.py set_fake_passwords --password admin || true
    touch ${SETUP_DONE_FILE}
    echo "Setup completed ..."
else
    echo "Setup was already done, skipping ..."
    # Wait for postgis
    wait-for-it -h postgis -p 5432 -t 60
fi

# Make sure data are readable:
chmod -R 777 ${DATASOURCE_PATH}
