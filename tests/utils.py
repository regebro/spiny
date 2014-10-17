import os
import shutil
import spiny
import tempfile

from ConfigParser import ConfigParser


class TestEnvironment(object):

    def __init__(self, env_list):
        self.env_list = env_list
        path = os.environ['PATH']
        self.pythons = spiny.environment.list_pythons_on_path(path)
        for env in self.env_list:
            if env not in self.pythons:
                raise EnvironmentError("You must have %s installed and "
                                       "on the path to run the tests." % env)

    def __enter__(self):
        self.test_dir = tempfile.mkdtemp()
        self.old_path = os.environ['PATH']
        os.environ['PATH'] = self.test_dir
        self.old_home = os.environ['HOME']
        os.environ['HOME'] = self.test_dir
        for env in self.env_list:
            path = self.pythons[env]['path']
            os.symlink(path, os.path.join(self.test_dir, env))
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        shutil.rmtree(self.test_dir)
        os.environ['PATH'] = self.old_path
        os.environ['HOME'] = self.old_home


def make_conf():
    conf = ConfigParser()
    conf.add_section('spiny')
    conf.add_section('pythons')
    return conf
