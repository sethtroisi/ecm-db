import datetime
import os
import logging
import time

import sqlite3

class EcmServer:
    """ECM Server

    Responsible for recording what curves have been run.
    """

    SCHEMA_FILE = "schema.sql"

    def __init__(db_file="ecm-server.db"):
        self.db_file = db_file
        self.db = None
        init_db()


    def init_db():
        self.db = sqlite3.connect(self.db_file)
        # Makes returns namedtuple like
        #self.db.row_factory = sqlite3.Row

        cur = self.db.cursor()

        if not os.path.isfile(self.db_file):
            logger.info(f"Creating db({self.db_file}) from {EcmServer.SCHEMA_FILE}")
            with open(EcmServer.SCHEMA_FILE) as schema_f:
                cur.executescript(schema_f.read())

