import datetime
import os
import logging
import re
import time

from enum import Enum

import gmpy2
import sqlite3

class EcmServer:
    """ECM Server

    Responsible for recording what curves have been run.
    """

    SCHEMA_FILE = "schema.sql"

    class Status(Enum):
        P = 1
        PRP = 2
        FF = 3
        CF = 4
        C = 5

    def __init__(self, db_file="./ecm-server.db"):
        self._db_file = db_file
        self._db = None

        self.init_db()


    def init_db(self):
        exists = os.path.isfile(self._db_file) and os.path.getsize(self._db_file) > 0

        self._db = sqlite3.connect(self._db_file)
        # Makes returns namedtuple like
        self._db.row_factory = sqlite3.Row

        # Turn on foreign_key constraints
        self._db.execute("PRAGMA foreign_keys = 1")

        if not exists:
            schema_path = os.path.join(os.path.dirname(__file__), EcmServer.SCHEMA_FILE)
            logging.warning(f"Creating db({self._db_file}) from {schema_path}")
            with open(schema_path) as schema_f:
                schema = schema_f.read()
                cur = self.get_cursor()
                cur.executescript(schema)
                cur.close()

    def get_cursor(self):
        # TODO: closing cursor one day.
        return self._db.cursor()

    def find_number(self, n):
        cur = self.get_cursor()
        cur.execute('SELECT * from INSERT INTO numbers VALUES (null,?,?,?)',
            (n, status))
        cur.close()
        self._db.commit()


    def add_number(self, expr):
        if EcmServer._is_number(expr):
            n = int(expr)
        else:
            raise ValueError(f"Bad expr: {expr}")

        # TODO: verify not already in db

        status = 2 if gmpy2.is_prime(n) else 5

        cur = self.get_cursor()
        cur.execute(
            'INSERT INTO numbers VALUES (null,?,?)',
            (n, status))
        cur.close()
        self._db.commit()

    def _is_number(n):
        return isinstance(n, int) or re.match("[1-9][0-9]*", n)

    def _is_number_expr(expr):
        # TODO
        # https://stackoverflow.com/questions/2371436/evaluating-a-mathematical-expression-in-a-string
        return False

