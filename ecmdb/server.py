import datetime
import os
import logging
import re
import time
import gmpy2

import sqlite3

class EcmServer:
    """ECM Server

    Responsible for recording what curves have been run.
    """

    SCHEMA_FILE = "schema.sql"

    def __init__(self, db_file="./ecm-server.db"):
        self.db_file = db_file
        self.db = None

        self.init_db()


    def init_db(self):
        exists = os.path.isfile(self.db_file)

        self.db = sqlite3.connect(self.db_file)
        # Makes returns namedtuple like
        self.db.row_factory = sqlite3.Row

        # Turn on foreign_key constraints
        self.db.execute("PRAGMA foreign_keys = 1")

        if not exists:
            schema_path = os.path.join(os.path.dirname(__file__), EcmServer.SCHEMA_FILE)
            logging.warn(f"Creating db({self.db_file}) from {schema_path}")
            with open(schema_path) as schema_f:
                schema = schema_f.read()
                cur = self.db.cursor()
                cur.executescript(schema)
                cur.close()

    def add_number(self, expr):
        # https://stackoverflow.com/questions/2371436/evaluating-a-mathematical-expression-in-a-string

        if re.match("[1-9][0-9]*", expr):
            # TODO: verify not already in db

            n = int(expr)
        else:
            # TODO: Implement
            short = str(expr)[:100]
            error = f"Not yet able to eval expr({short})"
            logging.error(error)
            raise NotImplementedError(error)

        status = 2 if gmpy2.is_prime(n) else 5

        cur = self.db.cursor()
        cur.execute(
            'INSERT INTO numbers VALUES (1,?,?,?)',
            (n, expr, status))
        cur.close()
        self.db.commit()

