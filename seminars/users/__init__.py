# -*- coding: utf-8 -*-

from __future__ import absolute_import
from .main import (login_page, login_manager, admin_required,
                  housekeeping)
assert admin_required  # silence pyflakes
assert housekeeping  # silence pyflakes
from flask_login import __version__ as FLASK_LOGIN_VERSION

from seminars.app import app
from lmfdb.logger import make_logger
from distutils.version import StrictVersion


# secret key, necessary for sessions, and sessions are
# in turn necessary for users to login
app.secret_key = 'vVjYyCM99DtirZqMaGMrle'

login_manager.init_app(app)

app.register_blueprint(login_page, url_prefix="/users")

users_logger = make_logger("users", hl=True)

FLASK_LOGIN_LIMIT = '0.3.0'
if StrictVersion(FLASK_LOGIN_VERSION) < StrictVersion(FLASK_LOGIN_LIMIT):
    raise RuntimeError("flask-login is older than version {version} and must be updated, perhaps through `sage -pip install flask-login`".format(version=FLASK_LOGIN_LIMIT))
