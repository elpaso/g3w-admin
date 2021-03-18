# coding=utf-8
""""App config for Openrouteservice

.. note:: This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

"""

__author__ = 'elpaso@itopen.it'
__date__ = '2021-03-09'
__copyright__ = 'Copyright 2021, ItOpen'


from django.apps import AppConfig
from django.core.exceptions import ImproperlyConfigured

class OpenrouteserviceConfig(AppConfig):
    name = 'openrouteservice'

    def ready(self):
        """Validate settings"""

        from django.conf import settings

        if not settings.hasattr('OSR_ENDPOINT') or settings.OSR_ENDPOINT == '':
            raise ImproperlyConfigured("OSR_ENDPOINT setting is not defined.")

        if not settings.hasattr('OSR_PROFILES') or type(settings.OSR_PROFILES) not in (list, tuple) or len(settings.OSR_PROFILES) == 0:
            raise ImproperlyConfigured(
                "OSR_PROFILES setting is not defined.")
