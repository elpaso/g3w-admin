from django.utils import six
from django.utils.translation import get_language
from django.views.generic import TemplateView
from django.template import loader
from django.shortcuts import get_object_or_404
from django.http import Http404, HttpResponseForbidden
from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.auth.views import redirect_to_login
from django.apps import apps
from django.core.exceptions import PermissionDenied
from rest_framework.renderers import JSONRenderer
from core.api.serializers import GroupSerializer, Group
from core.models import GeneralSuiteData
from usersmanage.utils import get_users_for_object, get_user_model
from copy import deepcopy


class ClientView(TemplateView):

    template_name = "{}/index.html".format(settings.CLIENT_DEFAULT)
    project = None

    def dispatch(self, request, *args, **kwargs):

        # check permissions
        project_app = apps.get_app_config(kwargs['project_type'])
        Project = project_app.get_model('project')

        # get project model object
        self.project = Project.objects.get(pk=kwargs['project_id']) if 'project_id' in kwargs else \
            Project.objects.get(slug=kwargs['project_slug'])

        grant_users = get_users_for_object(self.project, "view_project")

        anonymous_user = get_user_model().get_anonymous()

        if request.user not in grant_users and anonymous_user not in grant_users and not request.user.is_superuser:

            # redirect to login if Anonymous user
            if request.user.is_anonymous():
                return redirect_to_login(request.get_full_path(), settings.LOGIN_URL, 'next')
            else:
                raise PermissionDenied()

        return super(ClientView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        contextData = super(ClientView, self).get_context_data(**kwargs)

        # group serializer
        try:
            group = self.project.group
        except:
            group = get_object_or_404(Group, slug=kwargs['group_slug'])
        groupSerializer = GroupSerializer(group, projectId=str(self.project.pk), projectType=kwargs['project_type'],
                                          request=self.request)

        groupData = deepcopy(groupSerializer.data)

        # choose client by querystring paramenters
        contextData['client_default'] = self.get_client_name()

        # add user login data
        u = self.request.user
        user_data = {'i18n': get_language()}
        if not u.is_anonymous():
            user_data.update({
                'username': u.username,
                'first_name': u.first_name,
                'last_name': u.last_name,
                'groups': [g.name for g in u.groups.all()],
                'logout_url': reverse('logout'),
                'admin_url': reverse('home')
            })
        user_data = JSONRenderer().render(user_data)

        serializedGroup = JSONRenderer().render(groupData)
        if six.PY3:
            serializedGroup = str(serializedGroup, 'utf-8')

        baseurl = "/{}".format(settings.SITE_PREFIX_URL if settings.SITE_PREFIX_URL else '')
        frontendurl = ',"frontendurl":"{}"'.format(baseurl) if settings.FRONTEND else ''

        generaldata = GeneralSuiteData.objects.get()

        # add baseUrl property
        contextData['group_config'] = 'var initConfig ={{ "staticurl":"{}", "client":"{}", ' \
                                      '"mediaurl":"{}", "user":{}, "group":{}, "baseurl":"{}", "vectorurl":"{}", ' \
                                      '"main_map_title":{}, '"g3wsuite_logo_img"': "{}" {} }}'.\
            format(settings.STATIC_URL, "{}/".format(settings.CLIENT_DEFAULT), settings.MEDIA_URL, user_data,
                    serializedGroup, baseurl, settings.VECTOR_URL,
                   '"' + generaldata.main_map_title + '"' if generaldata.main_map_title else 'null',
                   settings.CLIENT_G3WSUITE_LOGO, frontendurl)

        # project by type(app)
        if not '{}-{}'.format(kwargs['project_type'], self.project.pk) in groupSerializer.projects.keys():
            raise Http404('No project type and/or project id present in group')

        # page title
        contextData['page_title'] = 'g3w-client | {}'.format(self.project.title)

        return contextData
        
    def get_template_names(self):
        return '{}/index.html'.format(self.get_client_name())
        
    def get_client_name(self):
        if 'client' in self.request.GET and self.request.GET['client'] in settings.CLIENTS_AVAILABLE:
            client = self.request.GET['client']
            try:
                loader.get_template('{}/index.html'.format(client))
                return client
            except:
                return settings.CLIENT_DEFAULT
        return settings.CLIENT_DEFAULT

