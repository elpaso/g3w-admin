from django.conf import settings
from defusedxml import lxml
from lxml import etree
from django.utils.translation import ugettext, ugettext_lazy as _
from core.utils.general import *
from django.db import transaction
from qdjango.models import Project
from .structure import *
import os, re
import json


def makeDatasource(datasource,layerType):
    """
    Rebuild datasource on qgjango/g3w-admin settings
    :param datasource:
    :param layerType:
    :return: string, new datasource
    """
    newDatasource = None
    # Path and folder name
    basePath = settings.DATASOURCE_PATH.rstrip('/') # eg: /home/sit/charts
    folder = os.path.basename(basePath) # eg: charts
    # OGR example datasource:
    # Original: <datasource>\\SIT-SERVER\sit\charts\definitivo\d262120.shp</datasource>
    # Modified: <datasource>/home/sit/charts\definitivo\d262120.shp</datasource>
    if layerType == Layer.TYPES.ogr or layerType == Layer.TYPES.gdal:
        newDatasource = re.sub(r'(.*?)%s(.*)' % folder, r'%s\2' % basePath, datasource) # ``?`` means ungreedy

    # SpatiaLite example datasource:
    # Original: <datasource>dbname='//SIT-SERVER/sit/charts/Carte stradali\\naturalearth_110m_physical.sqlite' table="ne_110m_glaciated_areas" (geom) sql=</datasource>
    # Modified: <datasource>dbname='/home/sit/charts/Carte stradali\\naturalearth_110m_physical.sqlite' table="ne_110m_glaciated_areas" (geom) sql=</datasource>
    if layerType == Layer.TYPES.spatialite:
        oldPath = re.sub(r"(.*)dbname='(.*?)'(.*)", r"\2", datasource) # eg: "//SIT-SERVER/sit/charts/Carte stradali\\naturalearth_110m_physical.sqlite"
        newPath = re.sub(r'(.*?)%s(.*)' % folder, r'%s\2' % basePath, oldPath) # eg: "\home\sit\charts/Carte stradali\\naturalearth_110m_physical.sqlite" (``?`` means ungreedy)
        newDatasource = datasource.replace(oldPath, newPath)

    return newDatasource


class QgisData(object):

    _dataToSet = []

    _introMessageException = ''


    def setData(self):
        """
        Set data to self object
        """
        for data in self._dataToSet:
            try:
                setattr(self,data,getattr(self,'_getData{}'.format(ucfirst(data)))())
            except Exception as e:
                raise Exception(_('{} "{}" {}:'.format(self._introMessageException,data,e.message)))


    def asXML(self):
        """
        Return data to xml format
        """
        pass



class QgisProjectLayer(QgisData):
    """
    Qgisdata obejct for layer project: a layer xml wrapper
    """

    _dataToSet = [
        'name',
        'layerId',
        'isVisible',
        'title',
        'layerType',
        'minScale',
        'maxScale',
        'scaleBasedVisibility',
        'srid',
        #'capabilities',
        'editOptions',
        'datasource',
        'columns'
    ]

    _introMessageException = 'Missing or invalid layer data'

    def __init__(self, layerTree, **kwargs):
        self.qgisProjectLayerTree = layerTree

        if 'qgisProject' in kwargs:
            self.qgisProject = kwargs['qgisProject']

        if 'order' in kwargs:
            self.order = kwargs['order']

        # set data value into this object
        self.setData()


    def _getDataName(self):
        """
        Get name tag content from xml
        :return: string
        """
        try:
            name = self.qgisProjectLayerTree.find('shortname').text
        except:
            name = self.qgisProjectLayerTree.find('layername').text
        return name

    def _getDataLayerId(self):
        """
        Get name tag content from xml
        :return: string
        """
        return self.qgisProjectLayerTree.find('id').text

    def _getDataTitle(self):
        """
        Get title tag content from xml
        :return: string
        """
        try:
            layer_title = self.qgisProjectLayerTree.find('layername').text
        except:
            layer_title = ''

        if layer_title == None:
            layer_title = ''

        return layer_title


    def _getDataIsVisible(self):
        """
        Get if is visible form xml
        :return: string
        """
        legendTrees = self.qgisProject.qgisProjectTree.find('legend')
        legends = legendTrees.iterdescendants(tag='legendlayerfile')

        for legend in legends:
            if legend.attrib['layerid'] == self.layerId:
                if legend.attrib['visible'] == '1':
                    return True
                else:
                    return False

    def _getDataLayerType(self):
        """
        Get name tag content from xml
        :return: string
        """
        availableTypes = [item[0] for item in Layer.TYPES]
        layerType = self.qgisProjectLayerTree.find('provider').text
        if not layerType in availableTypes:
            raise Exception(_('Missing or invalid type for layer')+' "%s"' % self.name)
        return layerType

    def _getDataMinScale(self):
        """
        Get min_scale from layer attribute
        :return: string
        """
        return int(float(self.qgisProjectLayerTree.attrib['maximumScale']))

    def _getDataMaxScale(self):
        """
        Get min_scale from layer attribute
        :return: string
        """
        return int(float(self.qgisProjectLayerTree.attrib['minimumScale']))

    def _getDataScaleBasedVisibility(self):
        """
        Get scale based visibility property from layer attribute
        :return: string
        """
        return bool(int(self.qgisProjectLayerTree.attrib['hasScaleBasedVisibilityFlag']))

    def _getDataSrid(self):
        """
        Get srid property of layer
        :return: string
        """
        try:
            srid = self.qgisProjectLayerTree.xpath('srs/spatialrefsys/srid')[0].text
        except:
            srid = None

        return int(srid)

    def _getDataCapabilities(self):



        return 1

    def _getDataEditOptions(self):

        editOptions = 0
        for editOp, layerIds in self.qgisProject.wfstLayers.items():
            if self.layerId in layerIds:
                editOptions |= getattr(settings,editOp)

        return None if editOptions == 0 else editOptions

    def _getDataDatasource(self):
        """
        Get name tag content from xml
        :return: string
        """
        datasource = self.qgisProjectLayerTree.find('datasource').text
        serverDatasource = makeDatasource(datasource,self.layerType)

        if serverDatasource is not None:
            return serverDatasource
        else:
            return datasource

    def _getDataColumns(self):
        """
        Retrive data about columns for db table or ogr lyer type
        :return:
        """
        if self.layerType in [Layer.TYPES.postgres,Layer.TYPES.spatialite]:
            layerStructure = QgisDBLayerStructure(self, layerType=self.layerType)
        elif self.layerType in [Layer.TYPES.ogr]:
            layerStructure = QgisOGRLayerStructure(self)

        if len(layerStructure.columns) > 0:
            layerStructure.columns += self._getLayerJoinedColumns()

        return layerStructure.columns


    def _getLayerJoinedColumns(self):

        joined_columns = []
        try:
            joins = self.qgisProjectLayerTree.find('vectorjoins')
            for join in joins:
                join_id = join.attrib['joinLayerId']

                # prendo l'elemento parent di un tag "id" dove il testo corrisponde al nome del layer
                joined_layer = self.qgisProjectLayerTree.getroottree().xpath('//id[text()="'+join_id+'"]/..')[0]
                joined_columns += []
        except Exception,e:
            pass
        return joined_columns

    def save(self):
        """
        Save o update layer instance into db
        :param instance:
        :param kwargs:
        :return:
        """

        columns = json.dumps(self.columns)

        self.instance, created = Layer.objects.get_or_create(
            name=self.name,
            project=self.qgisProject.instance,
            defaults={
                'title': self.title,
                'is_visible': self.isVisible,
                'layer_type': self.layerType,
                'qgs_layer_id': self.layerId,
                'min_scale': self.minScale,
                'max_scale': self.maxScale,
                'scalebasedvisibility': self.scaleBasedVisibility,
                'database_columns': columns,
                'srid': self.srid,
                'datasource': self.datasource,
                'order': self.order,
                'edit_options': self.editOptions
                }
            )
        if not created:
            self.instance.title = self.title
            self.instance.is_visible = self.isVisible
            self.instance.layer_type = self.layerType
            self.instance.qgs_layer_id = self.layerId
            self.instance.min_scale = self.minScale
            self.instance.max_scale = self.maxScale
            self.instance.scalebasedvisibility = self.scaleBasedVisibility
            self.instance.datasource = self.datasource
            self.instance.database_columns = columns
            self.instance.srid = self.srid
            self.instance.order = self.order
            self.instance.edit_options = self.editOptions
        # Save self.instance
        self.instance.save()


class QgisProjectValidator(object):
    """
    A simple qgis project validator call clean method
    """
    def __init__(self, qgisProject):
        self.qgisProject = qgisProject

    def clean(self):
       pass


class IsGroupCompatibleValidator(QgisProjectValidator):
    """
    Check il project is compatible with own group
    """
    def clean(self):
        if self.qgisProject.group.srid != self.qgisProject.srid:
            raise Exception(_('Project and group SRID must be the same'))
        if self.qgisProject.group.units != self.qgisProject.units:
            raise Exception(_('Project and group units must be the same'))


class ProjectExists(QgisProjectValidator):
    """
    Check il project exixts in database
    """
    def clean(self):
        from qdjango.models import Project
        if Project.objects.filter(title=self.qgisProject.title).exists():
            raise Exception(_('A project with the same title already exists'))


class ProjectExists(QgisProjectValidator):
    """
    Check il project exixts in database
    """
    def clean(self):
        if not self.qgisProject.title:
            raise Exception(_('Title porject not empty'))



class QgisProject(QgisData):
    """
    A qgis xml project file wrapper
    """
    _dataToSet = [
        'name',
        'title',
        'srid',
        'units',
        'initialExtent',
        'wfstLayers',
        'layersTree',
        'layers',
        'qgisVersion'
        ]

    _defaultValidators = [
        IsGroupCompatibleValidator
    ]

    _regexXmlLayer = 'projectlayers/maplayer[@geometry!="No geometry"]'

    _introMessageException = _('Invalid Project Data ')

    def __init__(self, qgis_file, **kwargs):
        self.qgisProjectFile = qgis_file
        self.validators = []
        self.instance = None

        #istance of a model Project
        if 'instance' in kwargs:
            self.instance = kwargs['instance']

        if 'group' in kwargs:
            self.group = kwargs['group']


        # try to load xml project file
        self.loadProject()

        # set data value into this object
        self.setData()

        #register defaul validator
        for validator in self._defaultValidators:
            self.registerValidator(validator)

    def loadProject(self):
        """
        Load projectfile by xml parser
        """
        try:

            # we have to rewind the underlying file in case it has been already parsed
            self.qgisProjectFile.file.seek(0)
            self.qgisProjectTree = lxml.parse(self.qgisProjectFile, forbid_entities=False)
        except Exception as e:
            raise Exception(_('The project file is malformed: {}'.format(e.message)))


    def _getDataName(self):
        """
        Get projectname from xml
        :return: string
        """
        return self.qgisProjectTree.getroot().attrib['projectname']

    def _getDataTitle(self):
        """
        Get title tag content from xml
        :return: string
        """
        return self.qgisProjectTree.find('title').text

    def _getDataInitialExtent(self):
        """
        Get start extention project from xml
        :return: dict
        """
        return {
            'xmin': self.qgisProjectTree.find('mapcanvas/extent/xmin').text,
            'ymin': self.qgisProjectTree.find('mapcanvas/extent/ymin').text,
            'xmax': self.qgisProjectTree.find('mapcanvas/extent/xmax').text,
            'ymax': self.qgisProjectTree.find('mapcanvas/extent/ymax').text
        }

    def _getDataSrid(self):
        """

        :return:
        """
        return int(self.qgisProjectTree.find('mapcanvas/destinationsrs/spatialrefsys/srid').text)

    def _getDataUnits(self):
        return self.qgisProjectTree.find('mapcanvas/units').text

    def _checkLayerTypeCompatible(self,layerTree):
        """
        Chek il layer is compatible for to show in webgis
        :param layerTree:
        :return:
        """
        if 'name' in layerTree.attrib:
            if layerTree.attrib['name'] == 'openlayers':
                return False
        if 'embedded' in layerTree.attrib:
            if layerTree.attrib['embedded'] == '1':
                return False
        return True

    def _getDataLayersTree(self):

        #get root of layer-tree-group
        layerTreeRoot = self.qgisProjectTree.find('layer-tree-group')

        def buildLayerTreeNodeObject(layerTreeNode):
            toRetLayers = []
            for level, layerTreeSubNode in enumerate(layerTreeNode):
                if level > 0:
                    toRetLayer = {
                        'name': layerTreeSubNode.attrib['name'],
                        'expanded': True if layerTreeSubNode.attrib['expanded'] == '1' else False
                    }
                    if layerTreeSubNode.tag == 'layer-tree-layer':
                        toRetLayer.update({
                            'id': layerTreeSubNode.attrib['id'],
                            'visible': True if layerTreeSubNode.attrib['checked'] == 'Qt::Checked' else False
                        })

                    if layerTreeSubNode.tag == 'layer-tree-group':
                        toRetLayer.update({
                            'nodes': buildLayerTreeNodeObject(layerTreeSubNode)
                        })
                    toRetLayers.append(toRetLayer)
            return toRetLayers

        return buildLayerTreeNodeObject(layerTreeRoot)

    def _getDataLayers(self):
        layers = []

        # Get layer trees
        layerTrees = self.qgisProjectTree.xpath(self._regexXmlLayer)

        for order,layerTree in enumerate(layerTrees):
            if self._checkLayerTypeCompatible(layerTree):
                layers.append(QgisProjectLayer(layerTree, qgisProject=self, order=order))

        return layers

    def _getDataQgisVersion(self):
        return self.qgisProjectTree.getroot().attrib['version']

    def _getDataWfstLayers(self):
        wfstLayers = {
            'INSERT': [],
            'UPDATE': [],
            'DELETE': []
        }

        wfstLayersTree = self.qgisProjectTree.xpath('properties/WFSTLayers')[0]

        # collect layer_id for edito ps
        for editOp in wfstLayers.keys():
            editOpsLayerIdsTree = wfstLayersTree.xpath('{}/value'.format(editOp.lower().capitalize()))
            for editOpsLayerIdTree in editOpsLayerIdsTree:
                wfstLayers[editOp].append(editOpsLayerIdTree.text)

        return wfstLayers


    def clean(self):
        for validator in self.validators:
            validator.clean()


    def registerValidator(self,validator):
        """
        Register a QgisProjectValidator object
        :param validator: QgisProjectValidator
        :return: None
        """
        self.validators.append(validator(self))

    def save(self,instance=None, **kwargs):
        """
        Save or update  qgisporject and layers into db
        :param instance: Project instance
        """

        thumbnail = kwargs.get('thumbnail')
        description = kwargs.get('description','')

        with transaction.atomic():
            if not instance and not self.instance:
                self.instance = Project.objects.create(
                    qgis_file=self.qgisProjectFile,
                    group=self.group,
                    title=self.title,
                    initial_extent=self.initialExtent,
                    thumbnail= thumbnail,
                    description=description,
                    qgis_version=self.qgisVersion,
                    layers_tree=self.layersTree
                )
            else:
                if instance:
                    self.instance = instance
                self.instance.qgis_file = self.qgisProjectFile
                self.instance.title = self.title
                self.instance.qgis_version = self.qgisVersion
                self.instance.initial_extent = self.initialExtent
                self.instance.layers_tree = self.layersTree

                if thumbnail:
                    self.instance.thumbnail = thumbnail
                if description:
                    self.instance.description = description

                self.instance.save()

            # Create or update layers
            for layer in self.layers:
                layer.save()

            # Pre-existing layers that have not been updated must be dropped
            newLayerNameList = [layer.name for layer in self.layers]
            for layer in self.instance.layer_set.all():
                if layer.name not in newLayerNameList:
                    layer.delete()

            # Update qgis file datasource for SpatiaLite and OGR layers
            self.updateQgisFileDatasource()

    def updateQgisFileDatasource(self):
        """Update qgis file datasource for SpatiaLite and OGR layers.

        SpatiaLite and OGR layers need their datasource string to be
        modified at import time so that the original path is replaced with
        the DjangoQGIS one (which is stored in ``settings.py`` as variable
        ``DATASOURCE_PATH``).

        Example original datasource::

        <datasource>\\SIT-SERVER\sit\charts\definitivo\d262120.shp</datasource>

        Example modified datasource::

        <datasource>/home/sit/charts\definitivo\d262120.shp</datasource>
        """

        # Parse the file and build the XML tree
        self.instance.qgis_file.file.seek(0)
        tree = lxml.parse(self.instance.qgis_file, forbid_entities=False)

        # Run through the layer trees
        for layer in tree.xpath(self._regexXmlLayer):
            if self._checkLayerTypeCompatible(layer):
                layerType = layer.find('provider').text
                datasource = layer.find('datasource').text

                newDatasource = makeDatasource(datasource,layerType)

                # Update layer
                if newDatasource:
                    layer.find('datasource').text = newDatasource

        # Update QGIS file
        with open(self.instance.qgis_file.path, 'w') as handler:
            tree.write(handler)


class QgisProjectSettingsWMS(QgisData):

    _dataToSet = [
        'layers'
    ]

    _NS = {
        'opengis': 'http://www.opengis.net/wms'
    }

    def __init__(self, project_settings, **kwargs):
        self.qgisProjectSettingsFile = project_settings

        # load data
        self.loadProjectSettings()

        # set data
        self.setData()

    def loadProjectSettings(self):
        """
        Load from 'string'  wms response request getProjectSettings
        :return:
        """
        try:
            self.qgisProjectSettingsTree = lxml.fromstring(self.qgisProjectSettingsFile)
        except Exception as e:
            raise Exception(_('The project settings is malformed: {}'.format(e.message)))

    def _buildTagWithNS(self,tag):
        return '{{{0}}}{1}'.format(self._NS['opengis'],'Name')

    def _getBBOXLayer(self, layerTree):

        bboxes = {}

        bboxTrees = layerTree.xpath(
            'opengis:BoundingBox',
            namespaces=self._NS
        )

        for bboxTree in bboxTrees:
            bboxes[bboxTree.attrib['CRS']] = {
                'minx': float(bboxTree.attrib['minx']),
                'miny': float(bboxTree.attrib['miny']),
                'maxx': float(bboxTree.attrib['maxx']),
                'maxy': float(bboxTree.attrib['maxy']),
            }

        return bboxes

    def _getLayerTreeData(self, layerTree):

        subLayerTrees = layerTree.xpath('opengis:Layer', namespaces=self._NS)
        if subLayerTrees:
            for subLayerTree in subLayerTrees:
                self._getLayerTreeData(subLayerTree)
        else:
            name = layerTree.find(self._buildTagWithNS('Name')).text
            dataLayer = {
                'name': name,
                'title': layerTree.find(self._buildTagWithNS('Title')).text,
                'visible': bool(int(layerTree.attrib['visible'])),
                'queryable': bool(int(layerTree.attrib['queryable'])),
                'bboxes': self._getBBOXLayer(layerTree)
            }
            self._layersData[name] = dataLayer

    def _getDataLayers(self):

        self._layersData = {}

        layersTree = self.qgisProjectSettingsTree.xpath(
            'opengis:Capability',
            namespaces=self._NS
        )

        self._getLayerTreeData(layersTree[0])
        return self._layersData


class QgisPgConnection(object):
    """
    Postgis xml interchange file
    """
    _version = "1.0"

    _params = {
        'port':5432,
        'saveUsername':'true',
        'password':'',
        'savePassword':'true',
        'sslmode':1,
        'service':'',
        'username':'',
        'host':'',
        'database':'',
        'name':'',
        'estimatedMetadata':'false'
    }

    def __init__(self, **kwargs):

        self._data = {}
        for k,v in kwargs.items():
            setattr(self,k,v)

    def __setattr__(self, key, value):

        if key in QgisPgConnection._params.keys():
            self.__dict__['_data'][key] = value
        else:
            self.__dict__[key] = value

    def __getattr__(self, key):

        if key in QgisPgConnection._params.keys():
            try:
                return self.__dict__['_data'][key]
            except:
                return QgisPgConnection._params[key]

        return self.__dict__[key]

    def asXML(self):

        qgsPgConnectionTree = etree.Element('qgsPgConnections', version=self._version)
        postgisTree = etree.Element('postgis')
        postgisTreeAttributes = postgisTree.attrib

        for key in QgisPgConnection._params.keys():
            postgisTreeAttributes[key] = str(getattr(self, key))

        qgsPgConnectionTree.append(postgisTree)

        return etree.tostring(qgsPgConnectionTree, doctype='<!DOCTYPE connections>')


