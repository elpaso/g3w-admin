# coding=utf-8
""""Constraints for single layers based on a rule and

.. note:: This program is free software; you can redistribute it and/or modify
          it under the terms of the Mozilla Public License 2.0.

"""

__author__ = 'elpaso@itopen.it'
__date__ = '2020-04-15'
__copyright__ = 'Copyright 2020, ItOpen'

import logging
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.db import connection, models, transaction
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from qdjango.models import Layer
from qdjango.apps import get_qgs_project

logger = logging.getLogger(__name__)

class Constraint(models.Model):
    """Main Constraint class. Stores the layer that is the target of a constraint
    and the constraint active state.
    """

    active = models.BooleanField(default=True)
    layer = models.ForeignKey(
        Layer, on_delete=models.CASCADE, related_name='constrainted_layer')

    @property
    def qgs_layer_id(self):
        """Return the QGIS layer id for the constrainted layer"""

        return self.layer.qgs_layer_id

    @property
    def layer_name(self):
        """Return the QGIS layer name for the constrainted layer"""

        return self.layer.name

    @property
    def rule_count(self):
        """Return the rules count for constrainted layer"""

        return self.constraintrule_set.count()

    def clean(self):
        pass

    def __str__(self):
        return "%s (%s)" % (self.layer, self.active)


    class Meta:
        managed = True
        verbose_name = _('Layer constraint')
        verbose_name_plural = _('Layer constraints')
        app_label = 'qdjango'


class ConstraintRule(models.Model):
    """Constraint rule class: links the constraint with a user or a group and
    defines the constraint SQL rule"""

    constraint = models.ForeignKey(Constraint, on_delete=models.CASCADE)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, blank=True, null=True, related_name='constrainted_rule_user')
    group = models.ForeignKey(
        Group, on_delete=models.CASCADE, blank=True, null=True, related_name='constrainted_rule_group')
    rule = models.TextField(_("SQL WHERE clause for the constrainted layer"), max_length=255)

    @property
    def active(self):
        """The rule is active if the constraint is"""

        return self.constraint.active

    def __str__(self):
        return "%s, %s: %s" % (self.constraint, self.user_or_group, self.rule)

    class Meta:
        managed = True
        verbose_name = _('Constraint rule')
        verbose_name_plural = _('Constraint rules')
        unique_together = (('constraint', 'user', 'rule'), ('constraint', 'group', 'rule'))
        app_label = 'qdjango'

    @property
    def user_or_group(self):
        """Returns the user or the group for this constraint"""

        if self.user:
            return self.user
        return self.group

    def clean(self):
        """Make sure either a group or a user are defined and that the SQL query runs without errors"""

        if self.group and self.user:
            raise ValidationError(
                _('You cannot define a user and a group at the same time'))

        if not self.group and not self.user:
            raise ValidationError(
                _('You must define a user OR a group'))

        sql_valid, ex = self.validate_sql()
        if not sql_valid:
            raise ValidationError(
                _('There is an error in the SQL rule where condition: %s' % ex ))


    @classmethod
    def get_constraints_for_user(cls, user, layer):
        """Fetch the constraints for a given user and layer

        :param user: the user
        :type user: User
        :param layer: the layer
        :type layer: Layer
        :return: a list of ConstraintRule
        :rtype: QuerySet
        """

        constraints = Constraint.objects.filter(layer=layer)
        if not constraints:
            return []
        user_groups = user.groups.all()
        if user_groups.count():
            return cls.objects.filter(Q(constraint__in=constraints), Q(user=user)|Q(group__in=user_groups))
        else:
            return cls.objects.filter(constraint__in=constraints, user=user)

    @classmethod
    def get_active_constraints_for_user(cls, user, layer):
        """Fetch the active constraints for a given user and layer

        :param user: the user
        :type user: User
        :param layer: the layer
        :type layer: Layer
        :return: a list of ConstraintRule
        :rtype: QuerySet
        """

        constraints = Constraint.objects.filter(layer=layer, active=True)
        if not constraints:
            return []
        user_groups = user.groups.all()
        if user_groups.count():
            return cls.objects.filter(Q(constraint__in=constraints), Q(user=user)|Q(group__in=user_groups))
        else:
            return cls.objects.filter(constraint__in=constraints, user=user)

    @classmethod
    def get_subsetstring_for_user(cls, user, qgs_layer_id):
        """Fetch the active constraints for a given user and QGIS layer id and returns the subset string or an empty string if there is no rule.

        :param user: the user
        :type user: User
        :param qgs_layer_id: QGIS map layer internal id
        :type qgs_layer_id: str
        :return: the subset string
        :rtype: str
        """

        try:
            constraints = Constraint.objects.filter(layer=Layer.objects.get(qgs_layer_id=qgs_layer_id), active=True)
        except Layer.DoesNotExist as ex:
            logger.error("A Layer object with QGIS layer id %s was not found: skipping constraints!" % qgs_layer_id)
            return ""

        if not constraints:
            return ""

        user_groups = user.groups.all()
        if user_groups.count():
            rules = cls.objects.filter(Q(constraint__in=constraints), Q(user=user)|Q(group__in=user_groups))
        else:
            rules = cls.objects.filter(constraint__in=constraints, user=user)

        subset_strings = []
        for rule in rules:
            subset_strings.append("(%s)" % rule.rule)

        subset_string = ' AND '.join(subset_strings)
        logger.debug("Returning subset string for user %s and layer %s: %s" % (user, qgs_layer_id, subset_string))
        return subset_string


    def validate_sql(self):
        """Checks if the rule can be executed without errors

        :raises ValidationError: error
        :return: (True, None) if rule has valid SQL, (False, ValidationError) if it is not valid
        :rtype: tuple (bool, ValidationError)
        """


        try:
            project = get_qgs_project(self.constraint.layer.project.qgis_file.path)
            if project is None:
                raise ValidationError("QGIS project not found: %s" % self.constraint.layer.project.qgis_file.path)
            layer = project.mapLayers()[self.constraint.layer.qgs_layer_id].clone()
            original_subset_string = layer.subsetString()
            if original_subset_string:
                subset_string = "(%s) AND (%s)" % (original_subset_string, self.rule)
            else:
                subset_string = self.rule
            if not layer.setSubsetString(subset_string):
                raise ValidationError("Could not set the subset string for layer %s: %s" % (self.constraint.layer.qgs_layer_id, subset_string))
            is_valid = layer.isValid()
            if not is_valid:
                raise ValidationError("QGIS layer %s is not valid after setting the new constraint: %s" % (self.constraint.layer.qgs_layer_id, subset_string))
        except Exception as ex:
            logger.debug('Validate SQL failed: %s' % ex)
            return False, ex
        return True, None
