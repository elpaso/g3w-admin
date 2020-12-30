from django import forms
from django.forms import ValidationError, widgets
from django.db.models import Q
from django.core.files.base import ContentFile
from django.utils.translation import ugettext, ugettext_lazy as _
from guardian.shortcuts import get_objects_for_user
from crispy_forms.helper import FormHelper, Layout
from crispy_forms.layout import Div, Field, HTML
from modeltranslation.forms import TranslationModelForm
from core.mixins.forms import *
from core.utils.forms import crispyBoxBaseLayer
from core.models import Group as G3WGroup
from usersmanage.forms import G3WACLForm
from usersmanage.utils import get_user_groups_for_object, get_groups_for_object
from django_file_form.forms import FileFormMixin, UploadedFileField
from .models import *
from usersmanage.utils import get_fields_by_user, crispyBoxACL, userHasGroups, get_viewers_for_object
from .utils.data import QgisProject
from .utils.validators import ProjectExists
import zipfile
import re


class QdjangoProjectFormMixin(object):
    """
    Mixin for project qdjango form, clean policy ofr qgisfile
    """
    def clean_qgis_file(self):
        try:
            qgis_file = self.cleaned_data['qgis_file']

            # validate extension
            file_extension = os.path.splitext(qgis_file.name)[1]
            if file_extension.lower() not in ('.qgs', '.qgz'):
                raise Exception(_("File must have 'qgs' or 'qgz' extension"))

            # for QGIS qgz file format
            if file_extension.lower() == '.qgz':
                zfile = zipfile.ZipFile(qgis_file, 'r')
                for fileinfo in zfile.infolist():
                    if os.path.splitext(fileinfo.filename)[1].lower() == '.qgs':
                        qzfile = fileinfo.filename

                # put qzfile to qgis_file
                qgis_file = ContentFile(zfile.open(qzfile, 'r').read(), name=qzfile)

                # Update path property for QGIS api
                qgis_file.path = self.cleaned_data['qgis_file'].file.path


            kwargs = {'group': self.group}
            if self.instance.pk:
                kwargs['instance'] = self.instance
            self.qgisProject = QgisProject(qgis_file, **kwargs)
            self.qgisProject.clean()
        except Exception as e:
            raise ValidationError(str(e))
        return qgis_file

    def clean_url_alias(self):
        url_alias = self.cleaned_data['url_alias']

        if url_alias:
            regex = re.compile(r'[\w-]+$')
            if not regex.match(url_alias):
                raise ValidationError(_("Url alias can contains only numbers, letters, - or _"))

            # check for unique
            if ProjectMapUrlAlias.objects.filter(alias=url_alias).exclude(app_name='qdjango', project_id=self.instance.pk).exists():
                raise ValidationError(_("This alias is used by another project/map"))
        return url_alias

    def clean_use_map_extent_as_init_extent(self):
        """ Check if init_map_extent is less bigger than max_extent """

        if hasattr(self, 'qgisProject'):
            initext = QgsRectangle(*self.qgisProject.initialExtent.values())
            maxext = QgsRectangle(*self.qgisProject.maxExtent.values()) if self.qgisProject.maxExtent else None
            if self.cleaned_data['use_map_extent_as_init_extent'] and maxext:
                if not maxext.contains(initext):
                    raise ValidationError(_('Max extent is smaller than init map extent'))

        return self.cleaned_data['use_map_extent_as_init_extent']

    def _save_url_alias(self):
        """
        Save url_alias if is set
        :return:
        """
        self.instance.url_alias = self.cleaned_data['url_alias']


class QdjangoProjectForm(TranslationModelForm, QdjangoProjectFormMixin, G3WFormMixin, G3WGroupFormMixin,
                        G3WGroupBaseLayerFormMixin, G3WRequestFormMixin, G3WACLForm, FileFormMixin, forms.ModelForm):

    qgis_file = UploadedFileField(required=True)
    thumbnail = UploadedFileField(required=False)
    url_alias = forms.CharField(
        required=False,
        label=_('URL alias'),
        help_text=_('You can set a human readable URL for the map. Only alphanumeric characters, not white space or '
                    'special characters')
    )

    def __init__(self, *args, **kwargs):
        if 'instance' in kwargs and hasattr(kwargs['instance'], 'url_alias'):
            kwargs['initial']['url_alias'] = kwargs['instance'].url_alias

        super(QdjangoProjectForm, self).__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.layout = Layout(
                            Div(
                                Div(
                                    Div(
                                        Div(
                                            HTML("<h3 class='box-title'><i class='ion ion-map'></i> {}</h3>"
                                                 .format(_('Qgis Project'))),
                                            css_class='box-header with-border'
                                        ),
                                        Div(
                                            'qgis_file',
                                            'form_id',
                                            'upload_url',
                                            'delete_url',
                                            css_class='box-body',

                                        ),
                                        css_class='box box-success'
                                    ),
                                    css_class='col-md-6'
                                ),

                                crispyBoxACL(self),
                                crispyBoxBaseLayer(self),

                                css_class='row'
                            ),
                            Div(
                                Div(
                                    Div(
                                        Div(
                                            HTML("<h3 class='box-title'><i class='fa fa-file'></i> {}</h3>"
                                                 .format(_('Description data'))),
                                            css_class='box-header with-border'
                                        ),
                                        Div(
                                            'title_ur',
                                            Field('description', css_class='wys5'),
                                            'thumbnail',
                                            HTML("""<img
                                            {% if not form.thumbnail.value %}style="display:none;"{% endif %}
                                            class="img-responsive img-thumbnail"
                                            src="{{ MEDIA_URL }}{{ form.thumbnail.value }}">""", ),
                                            'url_alias',
                                            css_class='box-body',
                                        ),
                                        css_class='box box-success'
                                    ),
                                    css_class='col-md-6'
                                ),

                                Div(
                                    Div(
                                        Div(
                                            HTML("<h3 class='box-title'><i class='ion ion-gear'></i> {}</h3>"
                                                 .format(_('Options and actions'))),
                                            css_class='box-header with-border'
                                        ),
                                        Div(
                                            'use_map_extent_as_init_extent',
                                            'context_base_legend',
                                            'feature_count_wms',
                                            'multilayer_query',
                                            'multilayer_querybybbox',
                                            'multilayer_querybypolygon',
                                            css_class='box-body',

                                        ),
                                        css_class='box box-success'
                                    ),
                                    css_class='col-md-6'
                                ),

                                css_class='row'
                            ),
        )

    class Meta:
        model = Project
        fields = (
            'qgis_file',
            'description',
            'thumbnail',
            'baselayer',
            'feature_count_wms',
            'multilayer_query',
            'multilayer_querybybbox',
            'multilayer_querybypolygon',
            'use_map_extent_as_init_extent',
            'context_base_legend',
            'title_ur'
        )

    def _setEditorUserQueryset(self):
        """
        Set query set for editors chosen fields
        :return: None
        """

        # add filter by group permissions
        editor_group = get_users_for_object(self.group, 'change_group', [G3W_EDITOR1])
        editor2_group = get_users_for_object(self.group, 'add_project_to_group', [G3W_EDITOR2])

        self.fields['editor_user'].queryset = get_objects_for_user(self.request.user, 'auth.change_user', User) \
            .filter(pk__in=[e.pk for e in editor_group], groups__name__in=self.editor1_groups)

        self.fields['editor2_user'].queryset = get_objects_for_user(self.request.user, 'auth.change_user', User) \
            .filter(pk__in=[e.pk for e in editor2_group], groups__name__in=self.editor2_groups)

    def _setViewerUserQueryset(self, **kwargs):
        """
        Set queryset for viewers chosen fields
        Take Viewers level 1 from Group
        :return: None
        """

        # get viewers from groups
        viewers = get_viewers_for_object(self.group, self.request.user, 'view_group')
        # get queryset
        self.fields['viewer_users'].queryset = User.objects.filter(groups__name__in=self.viewer_groups,
                                                                   pk__in=[v.pk for v in viewers])

    def _set_user_groups_queryset(self):
        """
        Set query set for viewer user groups chosen fields
        Take Viewer User Groups from Group
        :return: None
        """

        super(QdjangoProjectForm, self)._set_user_groups_queryset()

        editor_user_groups = get_user_groups_for_object(self.group, self.request.user, 'view_group', 'editor')
        self.fields['editor_user_groups'].queryset = AuthGroup.objects.filter(
            pk__in=[v.pk for v in editor_user_groups])

        viewer_user_groups = get_user_groups_for_object(self.group, self.request.user, 'view_group', 'viewer')
        self.fields['viewer_user_groups'].queryset = AuthGroup.objects.filter(
            pk__in=[v.pk for v in viewer_user_groups])

    def save(self, commit=True):
        self._ACLPolicy()

        self._save_url_alias()

        # add permission to Editor level 1 and 2 if current user is Editor level 1 or 2
        if userHasGroups(self.request.user, [G3W_EDITOR1, G3W_EDITOR2]):
            self.instance.addPermissionsToEditor(self.request.user)

            # give permission to Editor level 1 of group id user is Editor level 2
            if userHasGroups(self.request.user, [G3W_EDITOR2]):

                # give permission to user groups of map group
                user_editor_groups = get_groups_for_object(self.instance.group, 'view_group', 'editor')
                self.instance.add_permissions_to_editor_user_groups([uge.pk for uge in user_editor_groups])

                editor_users = get_users_for_object(self.instance.group, 'view_group', [G3W_EDITOR1, G3W_EDITOR2])
                for eu in editor_users:
                    self.instance.addPermissionsToEditor(eu)


class QdjangoWidgetForm(QdjangoProjectFormMixin, G3WFormMixin, G3WGroupFormMixin, G3WRequestFormMixin, forms.ModelForm):
    """
    Form object for Qdjango widget model.
    """

    def __init__(self, *args, **kwargs):
        super(QdjangoWidgetForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Div(
                Div(
                    'widget_type',
                    css_class='col-md-4'
                ),
                Div(
                    'name',
                    css_class='col-md-8'
                ),
                css_class='row'
            ),
            'body'
        )


    class Meta:
        model = Widget
        fields = (
            'widget_type',
            'name',
            'body'
        )
        widgets = {
            'body': widgets.HiddenInput
        }

