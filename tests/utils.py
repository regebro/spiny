import os
import shutil
import spiny
import tempfile

try:
    from ConfigParser import ConfigParser
except ImportError:
    from configparser import ConfigParser


class TestEnvironment(object):

    def __init__(self, env_list):
        self.env_list = env_list
        # By passing in an empty conf, we get the Pythons that are in the path only:
        conf = make_conf()
        conf.set('spiny', 'environments', ' '.join(env_list))
        self.pythons = spiny.environment.get_pythons(conf)

        for env in self.env_list:
            if env not in self.pythons:
                raise EnvironmentError("You must have %s installed and "
                                       "on the path to run the tests." % env)

    def __enter__(self):
        self.test_dir = tempfile.mkdtemp()
        try:
            self.old_path = os.environ['PATH']
            self.old_home = os.environ['HOME']
            os.environ['PATH'] = self.test_dir
            os.environ['HOME'] = self.test_dir
            for env in self.env_list:
                path = self.pythons[env]['path']
                os.symlink(path, os.path.join(self.test_dir, env))
            return self
        except Exception:
            # If there is an error here, __exit__ is never called,
            # so we need to cleanup.
            self._cleanup()

    def __exit__(self, exc_type, exc_value, traceback):
        self._cleanup()

    def _cleanup(self):
        os.environ['PATH'] = self.old_path
        os.environ['HOME'] = self.old_home
        shutil.rmtree(self.test_dir)


def make_conf():
    conf = ConfigParser()
    conf.add_section('spiny')
    conf.add_section('pythons')
    return conf
