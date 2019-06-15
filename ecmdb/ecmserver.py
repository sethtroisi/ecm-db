import contextlib
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
                with self.cursor() as cur:
                    cur.executescript(schema)


    def _get_cursor(self):
        # TODO: closing cursor one day.
        return self._db.cursor()


    def cursor(self):
        return contextlib.closing(self._get_cursor())


    def find_number(self, n):
        with self.cursor() as cur:
            cur.execute('SELECT * from numbers where n = ?', (n,))
            records = cur.fetchall()
            if len(records) == 0:
                return None
            elif len(records) >= 2:
                raise ValueError(f"Duplicate records for {n}")
            return records[0]


    def add_number(self, expr):
        if EcmServer._is_number(expr):
            n = int(expr)
        else:
            raise ValueError(f"Bad expr: {expr}")

        record = self.find_number(n)
        if record:
            return record

        status = 2 if gmpy2.is_prime(n) else 5

        with self.cursor() as cur:
            cur.execute('INSERT INTO numbers VALUES (null,?,?)', (n, status))
        self._db.commit()

        return self.find_number(n)

    def _is_number(n):
        return isinstance(n, int) or re.match("[1-9][0-9]*", n)

    def _is_number_expr(expr):
        # TODO
        # https://stackoverflow.com/questions/2371436/evaluating-a-mathematical-expression-in-a-string
        return False

