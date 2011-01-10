# This file is part of Elements.
# Copyright (c) 2010 Sean Kerr. All rights reserved.
#
# The full license is available in the LICENSE file that was distributed with this source code.
#
# Author: Sean Kerr <sean@code-box.org>

try:
    import cPickle as pickle

except:
    import pickle

import random
import string
import time

import settings

from elements.core.exception import ServerException

# ----------------------------------------------------------------------------------------------------------------------

class Session:

    def __init__ (self, session_id, backend=None):
        """
        Create a new Session instance.

        @param session_id (str)    The session id.
        @param backend    (object) The Session implementation instance.
        """

        self._session_id = session_id

    # ------------------------------------------------------------------------------------------------------------------

    def __delitem__ (self, name):
        """
        Remove a value.

        @param name (str) The name.
        """

        raise ServerException("Session.__delitem__() must be overridden")

    # ------------------------------------------------------------------------------------------------------------------

    def __getitem__ (self, name):
        """
        Retrieve a value.

        @param name (str) The name.

        @return (object) The value, if it exists, otherwise None.
        """

        raise ServerException("Session.__getitem__() must be overridden")

    # ------------------------------------------------------------------------------------------------------------------

    def __setitem__ (self, name, value):
        """
        Set a value.

        @param name  (str)    The name.
        @param value (object) The value.
        """

        raise ServerException("Session.__setitem__() must be overridden")

    # ------------------------------------------------------------------------------------------------------------------

    def get (self, name, default=None):
        """
        Retrieve a value. If the value does not exist, return the default value.

        @param name    (str)    The name.
        @param default (object) The default return value.

        @return (object) The value, if it exists, otherwise the default value.
        """

        raise ServerException("Session.get() must be overridden")

    # ------------------------------------------------------------------------------------------------------------------

    def is_authenticated (self):
        """
        Indicates that the session is authenticated.
        """

        raise ServerException("Session.is_authenticated() must be overridden")

    # ------------------------------------------------------------------------------------------------------------------

    def items (self):
        """
        Retrieve a dict of all name/value pairs.
        """

        raise ServerException("Session.items() must be overridden")

    # ------------------------------------------------------------------------------------------------------------------

    @classmethod
    def load (self, session_id=None):
        """
        Load a session.

        @param session_id (str) The session id.
        """

        raise ServerException("Session.load() must be overridden")

    # ------------------------------------------------------------------------------------------------------------------

    def merge (self, data):
        """
        Merge one or more name/value pairs into the session.

        @param data (dict) The dictionary of name/value pairs.
        """

        raise ServerException("Session.merge() must be overridden")

    # ------------------------------------------------------------------------------------------------------------------

    def save (self):
        """
        Save the session.
        """

        raise ServerException("Session.save() must be overridden")

    # ------------------------------------------------------------------------------------------------------------------

    @property
    def session_id (self):
        """
        Retrieve the session id.
        """

        return self._session_id

    # ------------------------------------------------------------------------------------------------------------------

    def set_authenticated (self, status):
        """
        Set the authenticated status.

        @param status (bool) Indicates that the session is authenticated.
        """

        raise ServerException("Session.set_authenticated() must be overridden")

# ----------------------------------------------------------------------------------------------------------------------

class MemcacheSession (Session):

    def __init__ (self, session_id, backend=None):
        """
        Create a new MemcacheSession instance.

        @param session_id (str)    The session id.
        @param backend    (object) The Session implementation instance.
        """

        Session.__init__(self, session_id)

        self._data     = dict()
        self._memcache = backend

    # ------------------------------------------------------------------------------------------------------------------

    def __delitem__ (self, name):
        """
        Remove a value.

        @param name (str) The name.
        """

        if name in self._data:
            del self._data[name]

            return

        raise ServerException("Non-existent key: %s" % name)

    # ------------------------------------------------------------------------------------------------------------------

    def __getitem__ (self, name):
        """
        Retrieve a value.

        @param name (str) The name.

        @return (object) The value, if it exists, otherwise None.
        """

        return self._data.get(name, None)

    # ------------------------------------------------------------------------------------------------------------------

    def __setitem__ (self, name, value):
        """
        Set a value.

        @param name  (str)    The name.
        @param value (object) The value.
        """

        self._data[name] = value

    # ------------------------------------------------------------------------------------------------------------------

    def get (self, name, default=None):
        """
        Retrieve a value. If the value does not exist, return the default value.

        @param name    (str)    The name.
        @param default (object) The default return value.

        @return (object) The value, if it exists, otherwise the default value.
        """

        return self._data.get(name, default)

    # ------------------------------------------------------------------------------------------------------------------

    def is_authenticated (self):
        """
        Indicates that the session is authenticated.
        """

        return self._data["__is_authenticated__"]

    # ------------------------------------------------------------------------------------------------------------------

    def items (self):
        """
        Retrieve a dict of all name/value pairs.
        """

        return self._data

    # ------------------------------------------------------------------------------------------------------------------

    @classmethod
    def load (self, session_id=None):
        """
        Load a session.

        @param session_id (str) The session id.
        """

        # connect to the memcache server
        try:
            import memcache

        except:
            raise ServerException("Failed to load memcache module")

        try:
            memcache = memcache.Client(settings.http_memcache_hosts)

        except Exception, e:
            raise ServerException("Cannot connect to memcache host: %s" % str(e))

        if session_id:
            # load an existing session
            data = memcache.get("session_" + session_id)

            if data:
                # session exists
                try:
                    data    = pickle.loads(data)
                    session = MemcacheSession(session_id, memcache)

                    session.merge(data)

                    return session

                except Exception, e:
                    raise ServerException("Failed to load session: %s" % str(e))

        # generate a new session id
        chars = "".join((string.letters, string.digits))

        while True:
            session_id = "".join([random.choice(chars) for x in xrange(0, 25)])

            if not memcache.get("session_" + session_id):
                # session id is available
                break

        # store the initial session data
        data    = { "__is_authenticated__": False }
        session = MemcacheSession(session_id, memcache)

        memcache.set("session_" + session_id, pickle.dumps(data))

        session.merge(data)

        return session

    # ------------------------------------------------------------------------------------------------------------------

    def merge (self, data):
        """
        Merge one or more name/value pairs into the session.

        @param data (dict) The dictionary of name/value pairs.
        """

        self._data.update(data)

    # ------------------------------------------------------------------------------------------------------------------

    def save (self):
        """
        Save the session.
        """

        try:
            self._memcache.set("session_" + self._session_id, pickle.dumps(self._data),
                               time=(settings.http_session_expiration * 60))

        except Exception, e:
            raise ServerException("Failed to save session: %s" % str(e))

    # ------------------------------------------------------------------------------------------------------------------

    def set_authenticated (self, status):
        """
        Set the authenticated status.

        @param status (bool) Indicates that the session is authenticated.
        """

        if status not in (True, False):
            raise ServerException("Invalid authenticated status")

        self._data["__is_authenticated__"] = status
