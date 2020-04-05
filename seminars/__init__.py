# -*- coding: utf-8 -*-
from __future__ import absolute_import
__version__ = '0.1'

import os, sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../lmfdb"))

#from .website import main
#assert main
from lmfdb.backend.database import PostgresDatabase
db = PostgresDatabase(dbname="beantheory")
assert db

# Have to make sure that changes aren't logged using the LMFDB's logging mechanism.
def nothing(self, **kwargs):
    pass
db.seminars.log_db_change = nothing
db.talks.log_db_change = nothing
db.institutions.log_db_change = nothing
