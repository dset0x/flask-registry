# -*- coding: utf-8 -*-
##
## This file is part of Flask-Registry
## Copyright (C) 2013, 2014 CERN.
##
## Flask-Registry is free software; you can redistribute it and/or
## modify it under the terms of the Revised BSD License; see LICENSE
## file for more details.

from __future__ import absolute_import

import os
import shutil
import sys
import tempfile

from flask.ext.registry import Registry, ModuleDiscoveryRegistry, \
    ImportPathRegistry, RegistryProxy, RegistryError, \
    ModuleAutoDiscoveryRegistry, ModuleRegistry

from .helpers import FlaskTestCase


class TestModuleDiscoveryRegistry(FlaskTestCase):
    def test_registration(self):
        Registry(app=self.app)

        self.app.extensions['registry'].update(
            pathns=ImportPathRegistry(initial=['flask_registry.*'])
        )

        self.assertEquals(3, len(self.app.extensions['registry']['pathns']))

        self.app.extensions['registry']['myns'] = \
            ModuleDiscoveryRegistry(
                'appdiscovery',
                registry_namespace='pathns')

        with self.app.app_context():
            self.app.extensions['registry']['myns'].discover()
            assert len(self.app.extensions['registry']['myns']) == 1
            from flask_registry.registries import appdiscovery
            assert self.app.extensions['registry']['myns'][0] == appdiscovery

        self.app.extensions['registry']['myns'].discover(app=self.app)

    def test_registration_noapp(self):
        Registry(app=self.app)

        self.app.extensions['registry']['myns'] = ModuleDiscoveryRegistry(
            'notimportant',
        )

        self.assertRaises(
            RegistryError,
            self.app.extensions['registry']['myns'].discover
        )

    def test_exclude(self):
        Registry(app=self.app)

        # Set exclude config
        self.app.config['PATH_NS_APPDISCOVERY_EXCLUDE'] = [
            'flask_registry.registries',
        ]

        self.app.extensions['registry'].update({
            'path.ns': ImportPathRegistry(initial=['flask_registry.*']),
            'myns': ModuleDiscoveryRegistry('appdiscovery',
                                            registry_namespace='path.ns')
        })

        with self.app.app_context():
            self.app.extensions['registry']['myns'].discover()
            assert len(self.app.extensions['registry']['myns']) == 0

    def test_missing_module(self):
        Registry(app=self.app)

        self.app.extensions['registry'].update(
            pathns=ImportPathRegistry(initial=['flask_registry.*']),
            myns=ModuleDiscoveryRegistry('some_non_existing_module',
                                         registry_namespace='pathns'))

        with self.app.app_context():
            self.app.extensions['registry']['myns'].discover()
            assert len(self.app.extensions['registry']['myns']) == 0

    def test_broken_module(self):
        Registry(app=self.app)

        self.app.extensions['registry'].update(
            pathns=ImportPathRegistry(initial=['tests']),
            myns=ModuleDiscoveryRegistry('broken_module',
                                         registry_namespace='pathns'))

        with self.app.app_context():
            self.assertRaises(ImportError,
                              self.app.extensions['registry']['myns'].discover)
            assert len(self.app.extensions['registry']['myns']) == 0

    def test_importing_package_that_indirectly_triggers_importerror_fails(self):
        # Nose flips if it cannot import a package and here we deliberately
        # want to test against a broken package. Therefore we use a temprary
        # directory elsewhere.

        # Append to sys
        tmp_path = tempfile.mkdtemp()
        sys.path.insert(0, tmp_path)

        # Create 'tmp_root', equivalent of 'tests'
        tmp_root = os.path.join(tmp_path, 'tmp_root')
        os.mkdir(tmp_root)
        with open(os.path.join(tmp_root, '__init__.py'), 'w') as init:
            init.write('')

        # Create the broken package.
        broken_pkg = os.path.join(tmp_root, 'broken_pkg')
        os.mkdir(broken_pkg)
        with open(os.path.join(broken_pkg, '__init__.py'), 'w') as init:
            init.write('from .broken_module import os')
        with open(os.path.join(broken_pkg, 'broken_module.py'), 'w') as bm:
            bm.write('import os;import bla_bla_bla_bla')

        # Run the test
        Registry(app=self.app)

        self.app.extensions['registry'].update(
            pathns=ImportPathRegistry(initial=['tmp_root']),
            myns=ModuleDiscoveryRegistry('broken_pkg',
                                         registry_namespace='pathns'))

        with self.app.app_context():
            self.assertRaises(ImportError,
                              self.app.extensions['registry']['myns'].discover)
            assert len(self.app.extensions['registry']['myns']) == 0

        # Clean up
        sys.path.pop(0)
        shutil.rmtree(tmp_path)


    def test_syntaxerror_module(self):
        Registry(app=self.app)

        self.app.extensions['registry'].update(
            pathns=ImportPathRegistry(initial=['tests']),
            myns=ModuleDiscoveryRegistry('syntaxerror_module',
                                         registry_namespace='pathns'))

        with self.app.app_context():
            self.assertRaises(
                SyntaxError,
                self.app.extensions['registry']['myns'].discover
            )
            assert len(self.app.extensions['registry']['myns']) == 0

        # Silence the error
        self.app.extensions['registry']['myns_silent'] = \
            ModuleDiscoveryRegistry('syntaxerror_module',
                                    registry_namespace='pathns',
                                    silent=True)

        with self.app.app_context():
            self.app.extensions['registry']['myns_silent'].discover()
            assert len(self.app.extensions['registry']['myns_silent']) == 0

    def test_modules_namespace(self):
        from flask_registry import registries
        Registry(app=self.app)

        self.app.extensions['registry']['pathns'] = ModuleRegistry()
        self.app.extensions['registry']['pathns'].register(registries)

        self.app.extensions['registry']['myns'] = \
            ModuleDiscoveryRegistry('appdiscovery',
                                    registry_namespace='pathns')

        with self.app.app_context():
            self.app.extensions['registry']['myns'].discover()
            assert len(self.app.extensions['registry']['myns']) == 1
            from flask_registry.registries import appdiscovery
            assert self.app.extensions['registry']['myns'][0] == appdiscovery

    def test_proxy_ns(self):
        Registry(app=self.app)

        proxy = RegistryProxy(
            'pathns',
            ImportPathRegistry,
            initial=['flask_registry.*']
        )

        with self.app.app_context():
            assert 'pathns' not in self.app.extensions['registry']

            self.app.extensions['registry']['myns'] = \
                ModuleDiscoveryRegistry('appdiscovery',
                                        registry_namespace=proxy)

            assert 'pathns' in self.app.extensions['registry']
            self.assertEqual(3, len(self.app.extensions['registry']['pathns']))

            self.app.extensions['registry']['myns'].discover()

            assert len(self.app.extensions['registry']['myns']) == 1
            from flask_registry.registries import appdiscovery
            assert self.app.extensions['registry']['myns'][0] == appdiscovery


class TestModuleAutoDiscoveryRegistry(FlaskTestCase):
    def test_registration(self):
        Registry(app=self.app)

        self.app.extensions['registry']['pathns'] = \
            ImportPathRegistry(initial=['flask_registry.*'])

        self.assertEqual(3, len(self.app.extensions['registry']['pathns']))

        self.app.extensions['registry']['myns'] = \
            ModuleAutoDiscoveryRegistry('appdiscovery',
                                        app=self.app,
                                        registry_namespace='pathns')

        assert len(self.app.extensions['registry']['myns']) == 1
        from flask_registry.registries import appdiscovery
        assert self.app.extensions['registry']['myns'][0] == appdiscovery

    def test_registry_proxy(self):
        Registry(app=self.app)

        self.app.extensions['registry']['pathns'] = \
            ImportPathRegistry(initial=['flask_registry.*'])

        myns = RegistryProxy(
            'myns', ModuleAutoDiscoveryRegistry, 'appdiscovery',
            registry_namespace='pathns'
        )

        with self.app.app_context():
            self.assertEqual(3, len(self.app.extensions['registry']['pathns']))
            self.assertEqual(1, len(list(myns)))
            from flask_registry.registries import appdiscovery
            self.assertEqual(appdiscovery, myns[0])
