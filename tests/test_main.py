import os
import shutil
import tempfile
import unittest

import spiny.main

class TestMainBase(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        shutil.copy(self.config_file, self.test_dir)
        os.chdir(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

class TestMinimal(unittest.TestCase):
    config_file = 'tests/configs/minimal.conf'

    def test_minimal(self):
        spiny.main.run(config_file=self.config_file)
