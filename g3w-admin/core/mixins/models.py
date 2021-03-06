
class G3WProjectMixins(object):

    def get_type(self):
        return self._meta.app_label


class G3WACLModelMixins(object):

    def addPermissionsToEditor(self, user):
        """
        Give guardian permissions to Editor
        """
        self._permissionsToEditor(user, 'add')

    def removePermissionsToEditor(self, user):
        """
        Remove guardian permissions to Editor
        """
        self._permissionsToEditor(user, 'remove')

    def addPermissionsToViewers(self, users_id):
        """
        Give guardian permissions to Viewers
        """
        self._permissionsToViewers(users_id, 'add')

    def removePermissionsToViewers(self, users_id):
        """
        Remove guardian permissions to Viewers
        """
        self._permissionsToViewers(users_id, 'remove')