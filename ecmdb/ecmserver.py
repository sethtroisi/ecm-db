import contextlib
import logging
import numbers
import os
import re

from enum import Enum

import gmpy2
import sqlite3

from flask import Flask, render_template, g


class EcmServer:
    """ECM Server

    Responsible for recording what curves have been run, and serving the website.
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
        self._app = self._init_webapp()


    def run(self, *args, **kwargs):
        return self._app.run(*args, **kwargs)

    # factory approach from https://flask.palletsprojects.com/en/3.0.x/patterns/appfactories/
    def _init_webapp(self):
        app = Flask(__name__, template_folder="../templates")

        @app.route("/", methods=["GET"])
        def main_page():
            status = self.status()
            self.add_number(300)
            return render_template(
                "index.html",
                status=status,
            )

        return app

    def _get_db(self):
        # application context db connection https://flask.palletsprojects.com/en/1.1.x/patterns/sqlite3/
        db = getattr(g, '_db', None)
        if db is None:
            exists = os.path.isfile(self._db_file) and os.path.getsize(self._db_file) > 0

            g._db = sqlite3.connect(self._db_file)
            # Makes returns namedtuple like
            g._db.row_factory = sqlite3.Row

            # Turn on foreign_key constraints
            g._db.execute("PRAGMA foreign_keys = 1")

            if not exists:
                schema_path = os.path.join(os.path.dirname(__file__), EcmServer.SCHEMA_FILE)
                logging.warning(f"Creating db({self._db_file}) from {schema_path}")
                with open(schema_path) as schema_f:
                    schema = schema_f.read()
                    with self.cursor() as cur:
                        cur.executescript(schema)
        return g._db


    def _cursor(self):
        return contextlib.closing(self._get_db().cursor())


    def find_number(self, n):
        """Find record for number if it's part of the database"""
        # TODO allow lookup by numid?
        with self._cursor() as cur:
            cur.execute('SELECT * from numbers where n = ?', (n,))
            records = cur.fetchall()

        if len(records) == 0:
            return None
        elif len(records) >= 2:
            raise ValueError(f"Duplicate records for {n}")
        return records[0]


    def add_number(self, expr):
        """Add a number to the database"""

        if EcmServer._is_number(expr):
            n = int(expr)
        else:
            raise ValueError(f"Bad expr: {expr}")

        record = self.find_number(n)
        if record:
            return record

        status = 2 if gmpy2.is_prime(n) else 5

        with self._cursor() as cur:
            cur.execute('INSERT INTO numbers VALUES (null,?,?)', (n, status))
        self._get_db().commit()

        return self.find_number(n)

    def status(self):
        with self._cursor() as cur:
            # TODO add t-level or some level of ecm summary
            cur.execute('SELECT numbers.* FROM numbers')
            records = cur.fetchall()
        return records


    def stats(self, expr):
        """Statistics about number, ecm progress, factors"""
        # TODO look up parents and all that jazz.

        # TODO wrapper class
        number = self.find_number(expr)
        if not number:
            return []
        num_id = number['num_id']

        with self.cursor() as cur:
            cur.execute('SELECT * from ecm_curves where num_id = ?', (num_id,))
            records = cur.fetchall()
        return records


    def _is_number(n):
        return isinstance(n, numbers.Integral) or re.match("[1-9][0-9]*", n)


    def _is_number_expr(expr):
        # TODO
        # https://stackoverflow.com/questions/2371436/evaluating-a-mathematical-expression-in-a-string
        return False



if __name__ == '__main__':
    server = EcmServer()
    # TODO allow config of port and host via ini or argparse
    server.run(host="0.0.0.0", port=8000, debug=True)
