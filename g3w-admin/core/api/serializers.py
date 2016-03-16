from django.conf import settings
from django.apps import apps
from rest_framework import serializers
from core.models import Group



class GroupSerializer(serializers.ModelSerializer):

    minscale = serializers.IntegerField(source='min_scale', read_only=True)
    maxscale = serializers.IntegerField(source='max_scale', read_only=True)
    crs = serializers.IntegerField(source='srid', read_only=True)

    def to_representation(self, instance):
        ret = super(GroupSerializer, self).to_representation(instance)

        # add projects to group
        ret['projects'] = []

        for g3wProjectApp in settings.G3WADMIN_PROJECT_APPS:
            Project = apps.get_app_config(g3wProjectApp).get_model('project')
            projects = Project.objects.all()
            for project in projects:
                ret['projects'].append({
                    'id': '{}-{}'.format(g3wProjectApp,project.id),
                    'title': project.title
                })

        # add initproject and overviewproject
        ret['initproject'] = ''
        ret['overviewproject'] = ''

        return ret

    class Meta:
        model= Group
        fields = (
            'id',
            'name',
            'minscale',
            'maxscale',
            'crs'
        )

