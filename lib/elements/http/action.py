# This file is part of Elements.
# Copyright (c) 2010 Sean Kerr. All rights reserved.
#
# The full license is available in the LICENSE file that was distributed with this source code.
#
# Author: Sean Kerr <sean@code-box.org>

import os

from elements.http import response_code

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

    # ------------------------------------------------------------------------------------------------------------------

    def connect (self, client):
        """
        Handle a CONNECT request.

        @param client (HttpClient) The HttpClient instance.
        """

        client.response_code = self.__response_code

        client.compose_headers()
        client.write("<h1>%s</h1>" % self.__title)
        client.flush()

    # ------------------------------------------------------------------------------------------------------------------

    def delete (self, client):
        """
        Handle a DELETE request.

        @param client (HttpClient) The HttpClient instance.
        """

        client.response_code = self.__response_code

        client.compose_headers()
        client.write("<h1>%s</h1>" % self.__title)
        client.flush()

    # ------------------------------------------------------------------------------------------------------------------

    def get (self, client):
        """
        Handle a GET request.

        @param client (HttpClient) The HttpClient instance.
        """

        client.response_code = self.__response_code

        client.compose_headers()
        client.write("<h1>%s</h1>" % self.__title)
        client.flush()

    # ------------------------------------------------------------------------------------------------------------------

    def head (self, client):
        """
        Handle a HEAD request.

        @param client (HttpClient) The HttpClient instance.
        """

        client.response_code = self.__response_code

        client.compose_headers()
        client.write("<h1>%s</h1>" % self.__title)
        client.flush()

    # ------------------------------------------------------------------------------------------------------------------

    def options (self, client):
        """
        Handle a OPTIONS request.

        @param client (HttpClient) The HttpClient instance.
        """

        client.response_code = self.__response_code

        client.compose_headers()
        client.write("<h1>%s</h1>" % self.__title)
        client.flush()

    # ------------------------------------------------------------------------------------------------------------------

    def post (self, client):
        """
        Handle a POST request.

        @param client (HttpClient) The HttpClient instance.
        """

        client.response_code = self.__response_code

        client.compose_headers()
        client.write("<h1>%s</h1>" % self.__title)
        client.flush()

    # ------------------------------------------------------------------------------------------------------------------

    def put (self, client):
        """
        Handle a PUT request.

        @param client (HttpClient) The HttpClient instance.
        """

        client.response_code = self.__response_code

        client.compose_headers()
        client.write("<h1>%s</h1>" % self.__title)
        client.flush()

    # ------------------------------------------------------------------------------------------------------------------

    def trace (self, client):
        """
        Handle a TRACE request.

        @param client (HttpClient) The HttpClient instance.
        """

        client.response_code = self.__response_code

        client.compose_headers()
        client.write("<h1>%s</h1>" % self.__title)
        client.flush()

# ----------------------------------------------------------------------------------------------------------------------

class SecureHttpAction (HttpAction):

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

        self._fs_root = fs_root
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
            client.raise_error(response_code.HTTP_404)
