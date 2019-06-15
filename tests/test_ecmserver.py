from ecmdb.ecmserver import EcmServer

import os
import logging
import sqlite3
import tempfile
import unittest

class TestEcmServer(unittest.TestCase):
    """EcmServer test cases."""

    def setUp(self):
        self.tmp_f = tempfile.NamedTemporaryFile()
        self.tmp_path = self.tmp_f.name

        # Turn off 'creating DB' warning.
        logging.basicConfig(level=logging.ERROR)

        self.server = EcmServer(self.tmp_path)

        # Reset logging.
        logging.basicConfig(level=logging.WARN)


    def test_setup(self):
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


    def test_add_number(self):
        # Add a prime and not prime
        self.server.add_number("37")
        self.server.add_number("370")

        cur = self.server.get_cursor()
        cur.execute("SELECT n, status FROM numbers")
        numbers = list(map(tuple, cur.fetchall()))
        self.assertGreaterEqual(len(numbers), 2)

        self.assertIn(("37", EcmServer.Status.PRP.value), numbers)
        self.assertIn(("370", EcmServer.Status.C.value), numbers)




if __name__ == '__main__':
    unittest.main()
