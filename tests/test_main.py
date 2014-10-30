import os
import shutil
import tempfile
import subprocess
import sys
import unittest

import spiny.main


class TestMainBase(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.run_dir = os.path.abspath(os.curdir)
        self.pkg_dir = os.path.join(self.test_dir, 'dinsdale')
        self.use_config = os.path.join(self.pkg_dir, os.path.split(self.config_file)[-1])

        shutil.copytree('tests/package', self.pkg_dir)
        shutil.copy(self.config_file, self.pkg_dir)
        os.chdir(self.pkg_dir)
        spiny.main.setup_logging(0, 2)

    def tearDown(self):
        shutil.rmtree(self.test_dir)
        os.chdir(self.run_dir)


class TestMinimal(TestMainBase):
    config_file = 'tests/configs/minimal.conf'

    def test_minimal(self):
        venv_dir = os.path.join(self.test_dir, '.venv')
        sys.argv = [sys.executable, '-qq', '-c', self.use_config,
                    'spiny:venv-dir=%s' % venv_dir]
        spiny.main.main()
        self.assertTrue(os.path.isdir(venv_dir),
                        "The .venv directory was not created")
        self.assertListEqual(['python2.7'], os.listdir(venv_dir))


class TestDual(TestMainBase):
    config_file = 'tests/configs/dual.conf'

    def test_minimal(self):
        venv_dir = os.path.join(self.test_dir, '.venv')
        sys.argv = [sys.executable, '-qq', '-c', self.use_config,
                    'spiny:venv-dir=%s' % venv_dir]
        spiny.main.main()
        self.assertTrue(os.path.isdir(venv_dir),
                        "The .venv directory was not created")
        self.assertListEqual(['python2', 'python3'], sorted(os.listdir(venv_dir)))
