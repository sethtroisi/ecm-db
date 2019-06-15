from ecmdb.ecmserver import EcmServer

import os
import sqlite3
import tempfile
import unittest

class TestEcmServer(unittest.TestCase):
    """EcmServer test cases."""
    def setUp(self):
        self.tmp_f = tempfile.NamedTemporaryFile()
        self.tmp_path = self.tmp_f.name
        self.server = EcmServer(self.tmp_path)


    def test_setup(self):
        self.assertTrue(os.path.exists(self.tmp_path))

        with sqlite3.connect(self.tmp_path) as test_db:
            test_db.row_factory = sqlite3.Row
            test_cur = test_db.cursor()

            server_cur = self.server.get_cursor()

            for cur in [server_cur, test_cur]:
                cur.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
                tables = cur.fetchall()
                tables = [row['name'] for row in tables]
                self.assertIn("numbers", tables)
                self.assertIn("factors", tables)
                self.assertIn("ecm_curves", tables)


if __name__ == '__main__':
    unittest.main()
