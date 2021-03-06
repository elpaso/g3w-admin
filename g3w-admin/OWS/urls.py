from django.conf.urls import url
from .views import *

urlpatterns = [
    # url working for qgis wms client
    url(r'^ows/(?P<group_slug>[-_\w\d]+)/(?P<project_type>[-_\w\d]+)/(?P<project_id>[-_\w\d]+)/&$', OWSView.as_view(),
        name='ows'),
    url(r'^ows/(?P<group_slug>[-_\w\d]+)/(?P<project_type>[-_\w\d]+)/(?P<project_id>[-_\w\d]+)/$', OWSView.as_view(),
        name='ows')
]
