# coding=utf-8
""""Openrouteservice utils

.. note:: This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

"""

__author__ = 'elpaso@itopen.it'
__date__ = '2021-03-09'
__copyright__ = 'Copyright 2021, ItOpen'

import requests
import json
import os
import re
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _
from qgis.core import (
    QgsJsonUtils,
    QgsVectorLayerUtils,
    QgsDataProvider,
    QgsMapLayerType,
    QgsWkbTypes,
    QgsProviderRegistry,
    QgsDataSourceUri,
    QgsVectorFileWriter,
    QgsVectorLayer,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProviderConnectionException,
    QgsGeometry,
)
from .models import ORS_REQUIRED_LAYER_FIELDS
from qdjango.models import Layer, QgisProjectFileLocker
from qgis.PyQt.QtCore import QTemporaryDir, QVariant

ORS_API_KEY = getattr(settings, 'ORS_API_KEY', None)


def is_ors_compatible(layer):
    """Check layer ORS compatibility"""

    if layer.type() != QgsMapLayerType.VectorLayer or layer.readOnly() or layer.geometryType() != QgsWkbTypes.PolygonGeometry:
        return False
    fields = layer.fields()
    for field_name, field_type in ORS_REQUIRED_LAYER_FIELDS.items():
        # Shapefile attributes max length is 10
        if layer.publicSource().endswith('.shp'):
            field_name = field_name[:10]
        if fields.lookupField(field_name) < 0 or not QVariant(fields.field(fields.lookupField(field_name)).type()).canConvert(field_type):
            return False
    return True


def db_connections(qgis_project):
    """Returns a dictionary of DB connections in the QGIS project, OGR connections with
    no "layername" specification are not  returned because by appending another layer we
    might break the project.

    Returned dictionary:

    {
        '<connection id>':
        {
            'id': "dbname='test_g3w-admin' host=localhost port=5432 user='ale' sslmode=disable schema='public'",
            'name': "test_g3w-admin (postgres host:localhost, port:5432, schema:'public')",
            'provider': 'postgres',
            'schema': 'public'
        }

    }

    Warning: the dictionary key may contain secrets(passwords): do not disclose to the client.

    :param qgis_project: QGIS vector layer instance
    :type qgis_project: QgsVectorLayer
    :return: dictionary of DB connections in the QGIS project
    :rtype:dict
    """

    connections = {}
    for vector_layer in [layer for layer in qgis_project.mapLayers().values() if layer.type() == QgsMapLayerType.VectorLayer and not layer.readOnly()]:

        dp = vector_layer.dataProvider()
        if dp is not None and bool(dp.capabilities() & QgsDataProvider.Database):

            # For OGR we have a file path
            if dp.name() == 'ogr':
                path = vector_layer.publicSource()
                if 'layername' in path.lower():
                    # Get base path: remove layername
                    path = re.sub(r'\|layername=.*$', '', path,  re.IGNORECASE)
                    name = os.path.basename(path)
                    connections[path] = {
                        'id': name,
                        'name': name,
                        'provider': dp.name(),
                    }

            else:
                md = QgsProviderRegistry.instance().providerMetadata(dp.name())

                if md is not None:

                    conn = md.createConnection(dp.uri().uri(), {})

                    if conn is not None:
                        uri = QgsDataSourceUri(dp.uri())
                        conn_id = conn.uri()

                        if dp.uri().schema():
                            conn_id += ' schema=\'%s\'' % dp.uri().schema()

                        details = []
                        for detail in ('service', 'host', 'port', 'schema'):
                            value = getattr(dp.uri(), detail)()
                            if value:
                                if detail == 'schema':
                                    # Quote schema
                                    value = '\'%s\'' % value
                                details.append('%s:%s' % (
                                    detail, value))
                        details = ', '.join(details)

                        conn_name = "{dbname} ({provider_name} {details})".format(
                            dbname=os.path.basename(uri.database()), provider_name=dp.name(), details=details)
                        if not conn_id in connections:
                            connections[conn_id] = {
                                'id': QgsDataSourceUri.removePassword(conn_id),
                                'name': conn_name,
                                'provider': dp.name(),
                                'schema': dp.uri().schema()
                            }

    return connections


def isochrone(profile, params):
    """Calls the isochrone ORS service and returns the response.

    Expected params (dict):

        {
            "locations":[[10.859513,43.401984]],
            "range_type":"time",
            "range":[480],
            "interval":60,
            "location_type":"start",
            "attributes":[
                "area",
                "reachfactor",
                "total_pop"  // <<--- currently not available
            ]
        }

    * "range": Maximum range value of the analysis in seconds for time and metres for distance.
               Alternatively a comma separated list of specific single range values if more than
               one location is set.
    * "locations": The locations to use for the route as an array of longitude/latitude pairs

    """

    headers = {
        'Accept': 'application/json, application/geo+json; charset=utf-8',
        'Content-Type': 'application/json; charset=utf-8'
    }

    json_params = params

    if ORS_API_KEY is not None:
        headers['Authorization'] = ORS_API_KEY

    response = requests.post(os.path.join(
        settings.ORS_API_ENDPOINT, 'isochrones', profile), json=json_params, headers=headers)
    return response


def add_geojson_features(geojson, project, qgis_layer_id=None, connection_id=None, new_layer_name=None):
    """Add geojson features to a destination layer, the layer can be specified
    by passing a QgsVectorLayer instance or by specifying a connection and
    a new layer name plus the QDjango project for the new layer.

    The connection can assume the special values `__shapefile__`, `__spatialite__` or `__geopackage__`
    for filesystem storage.

    The creation of the new layer may raise an exception is a layer with the same name as
    new_layer_name already exists.

    Returns the qgis_layer_id

    :param geojson: new features in GeoJSON format
    :type geojson: str
    :param project: QDjango Project instance for the new or the existing layer
    :type project: Project instance
    :param layer_id: optional, QGIS layer id
    :type layer_id: QGIS layer id
    :param connection: optional, connection id or the special value `__shapefile__`, `__spatialite__` or `__geopackage__`
    :type connection: str
    :param new_layer_name: optional, name of the new layer
    :type new_layer_name: str
    :raises Exception: raise on error
    :rtype: str
    """

    fields = QgsJsonUtils.stringToFields(geojson)

    # Create the new layer
    if connection_id is not None:

        def _write_to_ogr(destination_path, new_layer_name, driverName=None):
            """Writes features to new or existing OGR layer"""

            tmp_dir = QTemporaryDir()
            tmp_path = os.path.join(tmp_dir.path(), 'isochrone.json')
            with open(tmp_path, 'w+') as f:
                f.write(geojson)

            tmp_layer = QgsVectorLayer(tmp_path, 'tmp_isochrone', 'ogr')
            if not tmp_layer.isValid():
                raise Exception(
                    _('Cannot create temporary layer for isochrone result.'))

            # Note: shp attribute names are max 10 chars long
            save_options = QgsVectorFileWriter.SaveVectorOptions()
            if driverName is not None:
                save_options.driverName = driverName
            save_options.layerName = new_layer_name
            save_options.fileEncoding = 'utf-8'

            # This is nonsense to me: if the file does not exist the actionOnExistingFile
            # should be ignored instead of raising an error, probable QGIS bug
            if os.path.exists(destination_path):
                # Check if the layer already exists
                layer_exists = QgsVectorFileWriter.targetLayerExists(
                    destination_path, new_layer_name)

                if layer_exists:
                    raise Exception(
                        _('Cannot save isochrone result to destination layer: layer already exists (use "qgis_layer_id" instead)!'))

                save_options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer

            error_code, error_message = QgsVectorFileWriter.writeAsVectorFormatV2(
                tmp_layer,
                destination_path,
                project.qgis_project.transformContext(),
                save_options
            )

            if error_code != QgsVectorFileWriter.NoError:
                raise Exception(
                    _('Cannot save isochrone result to destination layer: ') + error_message)

            layer_uri = destination_path

            if driverName != 'ESRI Shapefile':
                layer_uri += '|layername=' + new_layer_name

            provider = 'ogr'
            return layer_uri, provider

        destination_path = None

        if connection_id == '__shapefile__':  # new shapefile
            driverName = 'ESRI Shapefile'
            extension = 'shp'
        elif connection_id == '__spatialite__':  # new sqlite
            driverName = 'SpatiaLite'
            extension = 'sqlite'
        elif connection_id == '__geopackage__':  # new gpkg
            driverName = 'GPKG'
            extension = 'gpkg'
        else:  # Add new table to an existing DB connection

            try:
                connection = db_connections(project.qgis_project)[
                    connection_id]
            except:
                raise Exception(
                    _('Wrong connection id.'))

            if connection['provider'] == 'ogr':
                destination_path = connection_id
                driverName = 'GPKG' if destination_path.lower().endswith(
                    '.gpkg') else 'SpatiaLite'
            else:
                driverName = None

        # Create a new file/layer
        if driverName is not None:
            new_layer_name = os.path.basename(new_layer_name)

            if destination_path is None:  # new files!
                destination_path = os.path.join(
                    settings.DATASOURCE_PATH, "{}.{}".format(new_layer_name, extension))
                i = 0
                while os.path.exists(destination_path):
                    i += 1
                    destination_path = os.path.join(
                        settings.DATASOURCE_PATH, "{}_{}.{}".format(new_layer_name, i, extension))

            layer_uri, provider = _write_to_ogr(
                destination_path, new_layer_name, driverName)

        # Create a new DB table
        else:
            assert connection['provider'] != 'ogr'
            md = QgsProviderRegistry.instance().providerMetadata(
                connection['provider'])
            if not md:
                raise Exception(
                    _('Error creating destination layer connection.'))
            conn = md.createConnection(connection_id, {})
            try:
                conn.createVectorTable(
                    connection['schema'], new_layer_name, fields, QgsWkbTypes.Polygon, QgsCoordinateReferenceSystem(4326), False, {'geometryColumn': 'geom'})
            except QgsProviderConnectionException:
                raise Exception(
                    _('Error creating destination layer: ') + str(QgsProviderConnectionException))

            uri = QgsDataSourceUri(conn.uri())
            uri.setTable(new_layer_name)
            uri.setSchema(connection['schema'])
            uri.setSrid('4326')
            uri.setGeometryColumn('geom')
            provider = connection['provider']
            layer_uri = uri.uri()

        # Now reload the new layer and add it to the project
        layer = QgsVectorLayer(layer_uri, new_layer_name, provider)

        with QgisProjectFileLocker(project) as project:
            project.qgis_project.addMapLayers([layer])
            project.update_qgis_project()

        qgis_layer_id = layer.id()

        if not layer.isValid():
            raise Exception(
                _('Error creating destination layer: layer is not valid!'))

        # Create Layer object
        instance, created = Layer.objects.get_or_create(
            qgs_layer_id=qgis_layer_id,
            project=project,
            defaults={
                'origname': new_layer_name,
                'name': new_layer_name,
                'title': new_layer_name,
                'is_visible': True,
                'layer_type': provider,
                'srid': 4326,
                'datasource': layer_uri
            })

        if not created:
            raise Exception(
                _('Error adding destination Layer to the project: layer already exists.'))

        qgis_layer_id = layer.id()

        # for OGR (already filled with features) returns the id of the new layer
        if driverName is not None:
            return qgis_layer_id

    # Append to an existing layer
    qgis_layer = project.qgis_project.mapLayer(qgis_layer_id)

    features = QgsJsonUtils.stringToFeatureList(
        geojson, fields)

    compatible_features = []
    for f in features:
        compatible_features.extend(
            QgsVectorLayerUtils.makeFeatureCompatible(f, qgis_layer))

    if qgis_layer.crs().isValid() and qgis_layer.crs() != QgsCoordinateReferenceSystem(4326):
        ct = QgsCoordinateTransform(QgsCoordinateReferenceSystem(
            4326), qgis_layer.crs(), project.qgis_project)
        for f in compatible_features:
            geom = f.geometry()
            if geom.transform(ct) != QgsGeometry.Success:
                raise Exception(
                    _('Error transforming geometry from 4326 to destination layer CRS.'))
            f.setGeometry(geom)

    if len(compatible_features) == 0:
        raise Exception(_('No compatible features returned from isochrone.'))

    if not qgis_layer.startEditing():
        raise Exception(_('Destination layer is not editable.'))

    # Add features to the layer
    if not qgis_layer.addFeatures(compatible_features):
        raise Exception(_('Error adding features to the destination layer.'))

    if not qgis_layer.commitChanges():
        raise Exception(
            _('Error committing features to the destination layer.'))

    return qgis_layer.id()
