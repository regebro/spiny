import unittest
import subprocess
import os

from spiny import environment
from .utils import TestEnvironment
from .utils import make_conf


class TestTestEnvironment(unittest.TestCase):
    """Check that the TestEnvironment context manager works"""
    def test_find_pythons(self):
        with TestEnvironment(['python2']):
            # Python 2 should be there:
            subprocess.Popen(['python2', '--version'],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
            self.assertRaises(OSError,
                              subprocess.call,
                              ['python3', '--version'])


class TestCustomPythons(unittest.TestCase):

    def test_custom_pythons(self):
        pythons = environment.list_pythons_on_path(os.environ['PATH'])
        python2 = pythons['python2']
        conf = make_conf()
        conf.set('pythons', 'python2', python2['path'])
        conf.set('spiny', 'environments', 'python2,python3')

        with TestEnvironment(['python3']):
            # This environment has only Python 3 on the path, but a specific
            # Python 2 config, so it should still work:
            environment.verify_environment(conf)


class TestEnvironmentChecks(unittest.TestCase):

    def test_pythons_exist(self):
        conf = make_conf()
        conf.set('spiny', 'environments', 'python2,python3')

        with TestEnvironment(['python2']) as env:
            self.assertRaises(EnvironmentError,
                              environment.verify_environment,
                              conf)

        with TestEnvironment(['python2', 'python3']) as env:
            environment.verify_environment(conf)
