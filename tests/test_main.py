import os
import shutil
import tempfile
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
        spiny.main.run(config_file=self.config_file,
                       overrides=['spiny:venv_dir=%s' % venv_dir])
        self.assertTrue(os.path.isdir(venv_dir),
                        "The .venv directory was not created")
