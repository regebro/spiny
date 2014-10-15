import os
import unittest
import shutil
import tempfile

import spiny.environment

class TestEnvironment(object):

    def __init__(self, env_list):
        self.env_list = env_list
        paths = os.environ['PATH'].split(os.pathsep)
        self.pythons = spiny.environment.list_pythons_on_path(paths)
        for env in self.env_list:
            if not env in self.pythons:
                raise EnvironmentError("You must have %s installed and on the path to run the tests." % env)

    def __enter__(self):
        self.test_dir = tempfile.mkdtemp()
        os.chdir(self.test_dir)
        self.old_path = os.environ['PATH']
        os.environ['PATH'] = self.test_dir

    def __exit__(self, exc_type, exc_value, traceback):
        shutil.rmtree(self.test_dir)
        os.environ['PATH'] = self.old_path


class TestEnvironmentChecks(unittest.TestCase):

    def test_find_pythons(self):
        # Uhhh...
        with TestEnvironment(['python2']) as env:
            pass
