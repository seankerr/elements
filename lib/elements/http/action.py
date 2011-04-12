# This file is part of Elements.
# Copyright (c) 2010 Sean Kerr. All rights reserved.
#
# The full license is available in the LICENSE file that was distributed with this source code.
#
# Author: Sean Kerr <sean@code-box.org>

import os

import settings

from elements.http  import response_code
from elements.model import database

# ----------------------------------------------------------------------------------------------------------------------

class HttpAction:

    def __init__ (self, server, title="Method Not Allowed", response_code=response_code.HTTP_405):
        """
        Create a new HttpAction instance.

        @param server        (HttpServer) The HttpServer instance.
        @param title         (str)        The title to display when this core action handles a request.
        @param response_code (str)        The response code to use when this core action handles a request.
        """

        self._server         = server
        self.__response_code = response_code
        self.__title         = title

        # add a few composite functions for quicker database access
        self.db_fetch_all      = database.fetch_all
        self.db_fetch_many     = database.fetch_many
        self.db_fetch_one      = database.fetch_one
        self.db_get_connection = database.get_connection

    # ------------------------------------------------------------------------------------------------------------------

    def connect (self, client):
        """
        Handle a CONNECT request.

        @param client (HttpClient) The HttpClient instance.
        """

        client.response_code = self.__response_code

        client.compose_headers()
        client.write("<html><head><title>%s</title></head><body><h1>%s</h1></body></html>" % \
                     (self.__title, self.__title))

    # ------------------------------------------------------------------------------------------------------------------

    def delete (self, client):
        """
        Handle a DELETE request.

        @param client (HttpClient) The HttpClient instance.
        """

        client.response_code = self.__response_code

        client.compose_headers()
        client.write("<html><head><title>%s</title></head><body><h1>%s</h1></body></html>" % \
                     (self.__title, self.__title))

    # ------------------------------------------------------------------------------------------------------------------

    def get (self, client):
        """
        Handle a GET request.

        @param client (HttpClient) The HttpClient instance.
        """

        client.response_code = self.__response_code

        client.compose_headers()
        client.write("<html><head><title>%s</title></head><body><h1>%s</h1></body></html>" % \
                     (self.__title, self.__title))

    # ------------------------------------------------------------------------------------------------------------------

    def head (self, client):
        """
        Handle a HEAD request.

        @param client (HttpClient) The HttpClient instance.
        """

        client.response_code = self.__response_code

        client.compose_headers()
        client.write("<html><head><title>%s</title></head><body><h1>%s</h1></body></html>" % \
                     (self.__title, self.__title))

    # ------------------------------------------------------------------------------------------------------------------

    def options (self, client):
        """
        Handle a OPTIONS request.

        @param client (HttpClient) The HttpClient instance.
        """

        client.response_code = self.__response_code

        client.compose_headers()
        client.write("<html><head><title>%s</title></head><body><h1>%s</h1></body></html>" % \
                     (self.__title, self.__title))

    # ------------------------------------------------------------------------------------------------------------------

    def post (self, client):
        """
        Handle a POST request.

        @param client (HttpClient) The HttpClient instance.
        """

        client.response_code = self.__response_code

        client.compose_headers()
        client.write("<html><head><title>%s</title></head><body><h1>%s</h1></body></html>" % \
                     (self.__title, self.__title))

    # ------------------------------------------------------------------------------------------------------------------

    def put (self, client):
        """
        Handle a PUT request.

        @param client (HttpClient) The HttpClient instance.
        """

        client.response_code = self.__response_code

        client.compose_headers()
        client.write("<html><head><title>%s</title></head><body><h1>%s</h1></body></html>" % \
                     (self.__title, self.__title))

    # ------------------------------------------------------------------------------------------------------------------

    def trace (self, client):
        """
        Handle a TRACE request.

        @param client (HttpClient) The HttpClient instance.
        """

        client.response_code = self.__response_code

        client.compose_headers()
        client.write("<html><head><title>%s</title></head><body><h1>%s</h1></body></html>" % \
                     (self.__title, self.__title))

# ----------------------------------------------------------------------------------------------------------------------

class SecureHttpAction (HttpAction):

    def check_auth (self, client):
        """
        Check the client authentication status.

        @param client (HttpClient) The HttpClient instance.

        @return (bool) True, if the client has been authenticated, otherwise False.
        """

        if not client.session or not client.session.is_authenticated():
            client.raise_response(response_code.HTTP_401)

            return False

        return True

    # ------------------------------------------------------------------------------------------------------------------

    def check_credentials (self, client):
        """
        Check the client credentials.

        @param client (HttpClient) The HttpClient instance.

        @return (bool) True, if the client has the required credentials, otherwise False.
        """

        return True

# ----------------------------------------------------------------------------------------------------------------------

class StaticHttpAction (HttpAction):

    def __init__ (self, fs_root, param="file", **kwargs):
        """
        Create a new StaticHttpAction instance.

        @param fs_root (str) The absolute filesystem path from which all static files will be served.
        @param param   (str) The parameter name to pull that contains the filename to serve.
        """

        HttpAction.__init__(self, **kwargs)

        self._fs_root = os.path.realpath(fs_root)
        self._param   = param

    # ------------------------------------------------------------------------------------------------------------------

    def get (self, client):
        """
        Handle a GET request.

        @param client (HttpClient) The HttpClient instance.
        """

        file = os.path.realpath("/".join((self._fs_root, client.params.get(self._param, "").strip(" /\\"))))

        if not file.startswith(self._fs_root) or file == self._fs_root or not client.serve_static_file(file):
            # wrong location or file doesn't exist/can't be opened for reading
            client.raise_response(response_code.HTTP_404)

# ----------------------------------------------------------------------------------------------------------------------

class TestHttpAction (HttpAction):

    def get (self, client):
        """
        Handle a GET request.

        @param client (HttpClient) The HttpClient instance.
        """

        import pprint

        pprint = pprint.PrettyPrinter(indent=4)

        client.compose_headers()
        client.write("<html><head><title>TestHttpAction</title></head><body>")
        client.write("<h1>client.in_headers</h1>")
        client.write("<pre>")
        client.write(pprint.pformat(client.in_headers))
        client.write("</pre>")
        client.write("<h1>client.out_headers</h1>")
        client.write("<pre>")
        client.write(pprint.pformat(client.out_headers))
        client.write("</pre>")
        client.write("<h1>client.in_cookies</h1>")
        client.write("<pre>")
        client.write(pprint.pformat(client.in_cookies))
        client.write("</pre>")
        client.write("<h1>client.out_cookies</h1>")
        client.write("<pre>")
        client.write(pprint.pformat(client.out_cookies))
        client.write("</pre>")
        client.write("<h1>client.params</h1>")
        client.write("<pre>")
        client.write(pprint.pformat(client.params))
        client.write("</pre>")
        client.write("<h1>client.files</h1>")
        client.write("<pre>")
        client.write(pprint.pformat(client.files))
        client.write("</pre>")
        client.write("</body></html>")

    # ------------------------------------------------------------------------------------------------------------------

    def post (self, client):
        """
        Handle a POST request.

        @param client (HttpClient) The HttpClient instance.
        """

        self.get(client)
