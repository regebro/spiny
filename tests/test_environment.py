import unittest
import subprocess

from spiny import environment
from .utils import TestEnvironment

try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser


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


class TestEnvironmentChecks(unittest.TestCase):

    def test_pythons_exist(self):
        conf = ConfigParser()
        conf.add_section('spiny')
        conf.set('spiny', 'environments', 'python2,python3')

        with TestEnvironment(['python2']) as env:
            self.assertRaises(EnvironmentError,
                              environment.verify_environment,
                              conf)
        with TestEnvironment(['python2', 'python3']) as env:
            environment.verify_environment(conf)
