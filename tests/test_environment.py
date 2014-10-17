import os
import subprocess
import unittest

from spiny import environment
from spiny import main
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
                              subprocess.Popen,
                              ['python3', '--version'],
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)


class TestEnvironmentChecks(unittest.TestCase):

    def test_pythons_exist(self):
        conf = make_conf()
        conf.set('spiny', 'environments', 'python2 python3')

        with TestEnvironment(['python2']) as env:
            self.assertRaises(EnvironmentError,
                              environment.get_pythons,
                              conf)

        with TestEnvironment(['python2', 'python3']) as env:
            environment.get_pythons(conf)

    def test_custom_pythons(self):
        pythons = environment.list_pythons_on_path(os.environ['PATH'])
        python2 = pythons['python2']
        conf = make_conf()
        conf.set('pythons', 'python2', python2['path'])
        conf.set('spiny', 'environments', 'python2 python3')

        with TestEnvironment(['python3']):
            # This environment has only Python 3 on the path, but a specific
            # Python 2 config, so it should still work:
            environment.get_pythons(conf)

    def test_wrong_custom_pythons(self):
        conf = make_conf()
        conf.set('pythons', 'python2', '/dev/null')
        conf.set('spiny', 'environments', 'python2 python3')

        self.assertRaises(EnvironmentError, environment.get_pythons, conf)

    def test_custom_python_version(self):
        pythons = environment.list_pythons_on_path(os.environ['PATH'])
        python2 = pythons['python2']
        conf = make_conf()
        conf.set('pythons', 'python2.2', python2['path'])
        conf.set('spiny', 'environments', 'python2 python3')

        self.assertRaises(EnvironmentError, environment.get_pythons, conf)

    def test_non_exec_pythons(self):
        conf = make_conf()
        conf.set('spiny', 'environments', 'python2 python3')

        with TestEnvironment(['python2', 'python3']) as env:
            # Touch a file that looks like it's python, but not an executable.
            with open(os.path.join(env.test_dir, 'python4'), mode='wb'):
                pass

            pythons = environment.get_pythons(conf)

        self.assertNotIn('python4', pythons)

    # This is not currently useful
    # The idea here is to make a test that exersizes the case when a Python install
    # does not have a virtualenv installed, and can't be installed with the
    # virtualenv that is installed with the python running the tests.
    # I'm not sure how to set up such an environment reliably.
    #def test_external_virtualenv(self):
        #conf = make_conf()
        #conf.set('spiny', 'environments', 'python2 python3')
        #pythons = environment.get_pythons(conf)

        #with TestEnvironment(['python2']) as env:
            ## Install a Python virtualenv:
            #main.install_virtualenvs(['python3'], pythons, env.test_dir)
            ## Set up so only that Python is on path
            #os.environ['PATH'] = os.path.join(env.test_dir, 'python3', 'bin')
            ## A virtualenv Python does not have virtualenv. However, this
            ## Should be installable with the virtualenv used by the python
            ## running these tests.
            #conf.set('spiny', 'environments', 'python3')
            #pythons = environment.get_pythons(conf)
