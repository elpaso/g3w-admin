from usersmanage.utils import get_users_for_object
from usersmanage.configs import *

class G3WACLViewMixin(object):
    '''
    Mixins for Class FormView for get user initial values for editors and viewers
    Use self property editor_permission and viewer_permission
    '''

    def get_form_kwargs(self):
        kwargs = super(G3WACLViewMixin, self).get_form_kwargs()
        kwargs['request'] = self.request

        # get viewer users
        viewers = get_users_for_object(self.object, self.viewer_permission, [G3W_VIEWER1, G3W_VIEWER2], with_anonymous=True)
        kwargs['initial']['viewer_users'] = [o.id for o in viewers]

        # get editor users
        if self.request.user.is_superuser:
            editor_users = get_users_for_object(self.object, self.editor_permission, [G3W_EDITOR2, G3W_EDITOR1])
            if editor_users:
                kwargs['initial']['editor_user'] = editor_users[0].id

        return kwargs