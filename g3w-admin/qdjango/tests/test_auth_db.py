# coding=utf-8
""""Auth DB tests

.. note:: This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

"""

__author__ = 'elpaso@itopen.it'
__date__ = '2020-12-30'
__copyright__ = 'Copyright 2020, Gis3w'


import json
import os

from django.conf import settings
from django.test import override_settings
from qgis.core import QgsApplication, QgsAuthMethodConfig, QgsDataSourceUri
from .base import CURRENT_PATH, TEST_BASE_PATH, QdjangoTestBase

# auth DB path
AUTH_DB_PATH = '/tmp/qgis-auth.db'
MASTER_PASSWORD_PATH = '/tmp/qgis_master_password.txt'

@override_settings(CACHES = {
        'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'some',
        }
    },
    LANGUAGE_CODE='en',
    LANGUAGES=(
        ('en', 'English'),
    ),
    QGIS_AUTH_DB_DIR_PATH='/tmp',
    # Full path to a file where the QGIS auth DB master password is saved, if the file does not exists it will be created (directory must be writeable from the server)
    # and the QGIS_AUTH_PASSWORD will be saved into the file.
    QGIS_AUTH_PASSWORD_FILE='/tmp/qgis_master_password.txt',
    # Define QGIS auth DB master password that will be placed into the QGIS_AUTH_PASSWORD_FILE if it does not exist.
    QGIS_AUTH_PASSWORD='my_secret_password'
)

class AuthDbTest(QdjangoTestBase):
    """Test QGIS Auth DB"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Prepare DB
        for path in (AUTH_DB_PATH, MASTER_PASSWORD_PATH):
            assert os.path.isfile(path)

        cls.am = QgsApplication.instance().authManager()
        assert cls.am.configIds() == []
        assert cls.am.setMasterPassword(True)
        assert cls.am.masterPasswordIsSet()

        config = QgsAuthMethodConfig()
        config.setName("alice")
        config.setMethod('Basic')
        config.setConfig("username", "my user" )
        config.setConfig("password", "my password" )
        assert config.isValid()

        res, cfg = cls.am.storeAuthenticationConfig(config)
        assert res
        assert config.id() != ''
        assert cfg.id() != ''
        assert cfg.id() == config.id()


    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        # Make sure there are no auth files left
        for path in (AUTH_DB_PATH, MASTER_PASSWORD_PATH):
            if os.path.isfile(path):
                os.unlink(path)

    def test_db_methods(self):
        """Test auth DB operations"""

        # Create an auth configuration
        config = QgsAuthMethodConfig()
        config.setName("alice")
        config.setMethod('Basic')
        config.setConfig("username", "my user" )
        config.setConfig("password", "my password" )
        self.assertTrue(config.isValid())

        res, cfg = self.am.storeAuthenticationConfig(config)
        self.assertTrue(res)
        self.assertTrue(config.id() != '')
        self.assertTrue(cfg.id() != '')
        self.assertEqual(cfg.id(), config.id())

        uri = QgsDataSourceUri('db=/my/fake/uri authcfg=%s' % cfg.id())
        self.assertEqual(uri.uri(True), "user='my user' password='my password' db='/my/fake/uri'")
        
