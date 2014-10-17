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
        shutil.copy(self.config_file, self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir)


class TestMinimal(TestMainBase):
    config_file = 'tests/configs/minimal.conf'

    def test_minimal(self):
        venv_dir = os.path.join(self.test_dir, '.venv')
        sys.argv = [sys.executable, '-c', self.config_file,
                    'spiny:venv_dir=%s' % venv_dir]
        spiny.main.main()
        self.assertTrue(os.path.isdir(venv_dir),
                        "The .venv directory was not created")
        self.assertListEqual(['python2.7'], os.listdir(venv_dir))

class TestDual(TestMainBase):
    config_file = 'tests/configs/dual.conf'

    def test_minimal(self):
        venv_dir = os.path.join(self.test_dir, '.venv')
        sys.argv = [sys.executable, '-c', self.config_file,
                    'spiny:venv_dir=%s' % venv_dir]
        spiny.main.main()
        self.assertTrue(os.path.isdir(venv_dir),
                        "The .venv directory was not created")
        self.assertListEqual(['python3', 'python2'], os.listdir(venv_dir))

