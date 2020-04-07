
from psycopg2 import DatabaseError
from flask import current_user


def is_locked(shortname):
    pass

def set_locked(shortname):
    pass

def get_lock(shortname, ignore_existence):
    from seminars.create import create_logger as logger
    lock = None
    if ignore_existence != "ignore":
        try:
            lock = is_locked(shortname)
        except DatabaseError as e:
            logger.info("Oops, failed to get the lock. Error: %s" % e)
    author_edits = lock and lock['email'] == current_user.email
    logger.debug(author_edits)
    if author_edits:
        lock = None
    if not lock:
        try:
            set_locked(shortname)
        except DatabaseError as e:
            logger.info("Oops, failed to set the lock. Error: %s" % e)
    return lock

