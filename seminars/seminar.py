
from flask import redirect, url_for
from flask_login import current_user
from seminars import db
from seminars.utils import search_distinct, lucky_distinct, count_distinct, allowed_shortname
from lmfdb.utils import flash_error
from psycopg2.sql import SQL


class WebSeminar(object):
    def __init__(self, shortname, data=None, editing=False, showing=False, saving=False):
        if data is None and not editing:
            data = seminars_lookup(shortname)
            if data is None:
                raise ValueError("Seminar %s does not exist" % shortname)
            data = dict(data.__dict__)
        self.new = (data is None)
        if self.new:
            self.shortname = shortname
            self.display = current_user.is_creator()
            self.online = True # default
            self.archived = False # don't start out archived
            self.is_conference = False # seminar by default
            for key, typ in db.seminars.col_type.items():
                if key == 'id' or hasattr(self, key):
                    continue
                elif typ == 'text':
                    setattr(self, key, '')
                elif typ == 'text[]':
                    setattr(self, key, [])
                else:
                    raise ValueError("Need to update seminar code to account for schema change")
        else:
            self.__dict__.update(data)

    def __repr__(self):
        return self.name

    def save(self):
        db.seminars.insert_many([{col: getattr(self, col, None) for col in db.seminars.search_cols}])

_selecter = SQL("SELECT {0} FROM (SELECT DISTINCT ON (shortname) {0} FROM {1} ORDER BY shortname, id DESC) tmp{2}")
_counter = SQL("SELECT COUNT(*) FROM (SELECT 1 FROM (SELECT DISTINCT ON (shortname) {0} FROM {1} ORDER BY shortname, id DESC) tmp{2}) tmp2")
def _construct(rec):
    if isinstance(rec, str):
        return rec
    else:
        return WebSeminar(rec['shortname'], data=rec)
def _iterator(cur, search_cols, extra_cols, projection):
    for rec in db.seminars._search_iterator(cur, search_cols, extra_cols, projection):
        yield _construct(rec)

def seminars_count(query={}):
    """
    Replacement for db.seminars.count to account for versioning.
    """
    return count_distinct(db.seminars, _counter, query)

def seminars_search(*args, **kwds):
    """
    Replacement for db.seminars.search to account for versioning, return WebSeminar objects.

    Doesn't support split_ors or raw.  Always computes count.
    """
    return search_distinct(db.seminars, _selecter, _counter, _iterator, *args, **kwds)

def seminars_lucky(*args, **kwds):
    """
    Replacement for db.seminars.lucky to account for versioning, return a WebSeminar object or None.
    """
    return lucky_distinct(db.seminars, _selecter, _construct, *args, **kwds)

def seminars_lookup(shortname, projection=3, label_col='shortname'):
    return seminars_lucky({label_col: shortname}, projection=projection)

def can_edit_seminar(shortname, new):
    """
    INPUT:

    - ``shortname`` -- the identifier of the seminar
    - ``new`` -- a boolean, whether the seminar is supposedly newly created

    OUTPUT:

    - ``resp`` -- a response to return to the user (indicating an error) or None (editing allowed)
    - ``seminar`` -- a WebSeminar object, as returned by ``seminars_lookup(shortname)``,
                     or ``None`` (if error or seminar does not exist)
    """
    if not allowed_shortname(shortname):
        flash_error("The seminar identifier must be nonempty and can only include letters, numbers, hyphens and underscores.")
        return redirect(url_for(".index"), 301), None
    seminar = seminars_lookup(shortname)
    # Check if seminar exists
    if new != (seminar is None):
        flash_error("Identifier %s %s" % (shortname, "already exists" if new else "does not exist"))
        return redirect(url_for(".index"), 301), None
    if not new and not current_user.is_admin():
        # Make sure user has permission to edit
        organizer_data = db.seminar_organizers.lucky({'shortname': shortname, 'email':current_user.email})
        if organizer_data is None:
            owner_name = db.users.lucky({'email': seminar.owner}, 'full_name')
            owner = "<%s>" % (owner_name, seminar.owner)
            if owner_name:
                owner = owner_name + " " + owner
            flash_error("You do not have permssion to edit seminar %s.  Contact the seminar owner, %s, and ask them to grant you permission." % (shortname, owner))
            return redirect(url_for(".index"), 301), None
    if seminar is None:
        seminar = WebSeminar(shortname, data=None, editing=True)
    return None, seminar
