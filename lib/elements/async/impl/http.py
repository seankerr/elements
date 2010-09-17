# This file is part of Elements.
# Copyright (c) 2010 Sean Kerr. All rights reserved.
#
# The full license is available in the LICENSE file that was distributed with this source code.
#
# Author: Sean Kerr <sean@code-box.org>

import datetime
import mimetypes
import os
import random
import re
import socket
import string
import time
import urllib
import urlparse

from elements.core           import elements
from elements.core.exception import ClientException
from elements.core.exception import HttpException
from elements.core.exception import ServerException
from elements.async.client   import Client
from elements.async.server   import Server

# ----------------------------------------------------------------------------------------------------------------------
# RESPONSE CODES
# ----------------------------------------------------------------------------------------------------------------------

HTTP_100 = "100 Continue"
HTTP_101 = "101 Switching Protocols"
HTTP_102 = "102 Processing"
HTTP_200 = "200 OK"
HTTP_201 = "201 Created"
HTTP_202 = "202 Accepted"
HTTP_203 = "203 Non-Authoritative Information"
HTTP_204 = "204 No Content"
HTTP_205 = "205 Reset Content"
HTTP_206 = "206 Partial Content"
HTTP_207 = "207 Multi-Status"
HTTP_226 = "226 IM Used"
HTTP_300 = "300 Multiple Choices"
HTTP_301 = "301 Moved Permanently"
HTTP_302 = "302 Found"
HTTP_303 = "303 See Other"
HTTP_304 = "304 Not Modified"
HTTP_305 = "305 Use Proxy"
HTTP_306 = "306 Reserved"
HTTP_307 = "307 Temporary Redirect"
HTTP_400 = "400 Bad Request"
HTTP_401 = "401 Unauthorized"
HTTP_402 = "402 Payment Required"
HTTP_403 = "403 Forbidden"
HTTP_404 = "404 Not Found"
HTTP_405 = "405 Method Not Allowed"
HTTP_406 = "406 Not Acceptable"
HTTP_407 = "407 Proxy Authentication Required"
HTTP_408 = "408 Request Timeout"
HTTP_409 = "409 Conflict"
HTTP_410 = "410 Gone"
HTTP_411 = "411 Length Required"
HTTP_412 = "412 Precondition Failed"
HTTP_413 = "413 Request Entity Too Large"
HTTP_414 = "414 Request-URI Too Long"
HTTP_415 = "415 Unsupported Media Type"
HTTP_416 = "416 Requested Range Not Satisfiable"
HTTP_417 = "417 Expectation Failed"
HTTP_422 = "422 Unprocessable Entity"
HTTP_423 = "423 Locked"
HTTP_424 = "424 Failed Dependency"
HTTP_426 = "426 Upgrade Required"
HTTP_500 = "500 Internal Server Error"
HTTP_501 = "501 Not Implemented"
HTTP_502 = "502 Bad Gateway"
HTTP_503 = "503 Service Unavailable"
HTTP_504 = "504 Gateway Timeout"
HTTP_505 = "505 HTTP Version Not Supported"
HTTP_506 = "506 Variant Also Negotiates"
HTTP_507 = "507 Insufficient Storage"
HTTP_510 = "510 Not Extended"

# ----------------------------------------------------------------------------------------------------------------------
# ERROR CODES
# ----------------------------------------------------------------------------------------------------------------------

ERROR_UPLOAD_MAX_SIZE = 1

# ----------------------------------------------------------------------------------------------------------------------
# MISC SETTINGS
# ----------------------------------------------------------------------------------------------------------------------

FILE_READ_SIZE = 131070

PERSISTENCE_KEEP_ALIVE = 1
PERSISTENCE_PROTOCOL   = 2

# ----------------------------------------------------------------------------------------------------------------------

class HttpAction:

    def __init__ (self, server, title="Method Not Allowed", response_code=HTTP_405):
        """
        Create a new HttpAction instance.

        @param server        (HttpServer) The HttpServer instance.
        @param title         (str)        The H1 title to display when this core action handles a request.
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

        client.write("HTTP %s\r\nServer: %s\r\n\r\n<h1>%s</h1>" % (self.__response_code, elements.APP_NAME,
                                                                   self.__title))
        client.flush()

    # ------------------------------------------------------------------------------------------------------------------

    def delete (self, client):
        """
        Handle a DELETE request.

        @param client (HttpClient) The HttpClient instance.
        """

        client.write("HTTP %s\r\nServer: %s\r\n\r\n<h1>%s</h1>" % (self.__response_code, elements.APP_NAME,
                                                                   self.__title))
        client.flush()

    # ------------------------------------------------------------------------------------------------------------------

    def get (self, client):
        """
        Handle a GET request.

        @param client (HttpClient) The HttpClient instance.
        """

        client.write("HTTP %s\r\nServer: %s\r\n\r\n<h1>%s</h1>" % (self.__response_code, elements.APP_NAME,
                                                                   self.__title))
        client.flush()

    # ------------------------------------------------------------------------------------------------------------------

    def head (self, client):
        """
        Handle a HEAD request.

        @param client (HttpClient) The HttpClient instance.
        """

        client.write("HTTP %s\r\nServer: %s\r\n\r\n<h1>%s</h1>" % (self.__response_code, elements.APP_NAME,
                                                                   self.__title))
        client.flush()

    # ------------------------------------------------------------------------------------------------------------------

    def options (self, client):
        """
        Handle a OPTIONS request.

        @param client (HttpClient) The HttpClient instance.
        """

        client.write("HTTP %s\r\nServer: %s\r\n\r\n<h1>%s</h1>" % (self.__response_code, elements.APP_NAME,
                                                                   self.__title))
        client.flush()

    # ------------------------------------------------------------------------------------------------------------------

    def post (self, client):
        """
        Handle a POST request.

        @param client (HttpClient) The HttpClient instance.
        """

        client.write("HTTP %s\r\nServer: %s\r\n\r\n<h1>%s</h1>" % (self.__response_code, elements.APP_NAME,
                                                                   self.__title))
        client.flush()

    # ------------------------------------------------------------------------------------------------------------------

    def put (self, client):
        """
        Handle a PUT request.

        @param client (HttpClient) The HttpClient instance.
        """

        client.write("HTTP %s\r\nServer: %s\r\n\r\n<h1>%s</h1>" % (self.__response_code, elements.APP_NAME,
                                                                   self.__title))
        client.flush()

    # ------------------------------------------------------------------------------------------------------------------

    def trace (self, client):
        """
        Handle a TRACE request.

        @param client (HttpClient) The HttpClient instance.
        """

        client.write("HTTP %s\r\nServer: %s\r\n\r\n<h1>%s</h1>" % (self.__response_code, elements.APP_NAME,
                                                                   self.__title))
        client.flush()

# ----------------------------------------------------------------------------------------------------------------------

class HttpClient (Client):

    def __init__ (self, client_socket, client_address, server, server_address):
        """
        Create a new HttpClient instance.

        @param client_socket  (socket) The client socket.
        @param client_address (tuple)  A two-part tuple containing the client ip and port.
        @param server         (Server) The Server instance within which this HttpClient is being created.
        @param server_address (tuple)  A two-part tuple containing the server ip and port to which the client has
                                       made a connection.
        """

        Client.__init__(self, client_socket, client_address, server, server_address)

        self._is_allowing_persistence = False               # indicates that this client allows persistence
        self._max_persistent_requests = None                # maximum persistent requests allowed
        self._multipart_file          = None                # current multipart upload file
        self._orig_read_delimiter     = self.read_delimiter # current read delimiter method
        self._request_count           = 0                   # count of served requests (only useful if persistence is
                                                            # enabled)

        # files variable must exist because it's access in handle_shutdown(), and handle_shutdown() is always called,
        # even in the event that a timeout occurred before a request could physically be handled
        self.__files = []

        self.read_delimiter("\r\n", self.handle_request, server._max_request_length)

    # ------------------------------------------------------------------------------------------------------------------

    def allow_persistence (self, status, max_requests=None):
        """
        Set the persistence status.

        @param status       (bool) The persistence status.
        @param max_requests (int)  The maximum persistent requests to serve before the connection will be closed.
        """

        self._is_allowing_persistence = status
        self._max_persistent_requests = max_requests

    # ------------------------------------------------------------------------------------------------------------------

    def compose_headers (self):
        """
        Compose the response headers.
        """

        out_headers = self.out_headers

        # required headers
        out_headers["Content-Type"] = self.content_type
        out_headers["Server"]       = elements.APP_NAME

        # handle persistence
        if self._max_persistent_requests and self._request_count >= self._max_persistent_requests:
            self._persistence_type = None

        elif self._is_allowing_persistence:
            if self._persistence_type:
                out_headers["Connection"] = "keep-alive"

            else:
                out_headers["Connection"] = "close"

        # build the request head
        head = " ".join((self.in_headers["SERVER_PROTOCOL"], self.response_code))

        for item in out_headers.items():
            head += "\r\n" + ": ".join(item)

        for cookie in self.out_cookies.values():
            head += "\r\nSet-Cookie: " + cookie

        self.write(head + "\r\n\r\n")

    # ------------------------------------------------------------------------------------------------------------------

    def handle_dispatch (self):
        """
        This callback is executed when the request has been parsed and needs dispatched to a handler.
        """

        raise ClientException("HttpClient.handle_dispatch() must be overridden")

    # ------------------------------------------------------------------------------------------------------------------

    def handle_headers (self, data):
        """
        This callback is executed when the client headers need to be parsed.

        @param data The data that has tentatively been found as the HTTP headers.
        """

        try:
            in_cookies = self.in_cookies
            in_headers = self.in_headers

            # parse headers
            for header in data.rstrip().split("\r\n"):
                header = header.split(": ")

                in_headers["HTTP_" + header[0].upper().replace("-", "_")] = header[1]

            # parse cookies
            if "HTTP_COOKIE" in in_headers:
                for cookie in in_headers["HTTP_COOKIE"].split(";"):
                    cookie = cookie.rstrip().split("=", 1)

                    in_cookies[cookie[0]] = cookie[1]

            # check persistence
            if in_headers["SERVER_PROTOCOL"] == "HTTP/1.1":
                self._persistence_type = PERSISTENCE_PROTOCOL

            elif in_headers.get("HTTP_CONNECTION", "").lower() == "keep-alive":
                self._persistence_type = PERSISTENCE_KEEP_ALIVE

            # check content type
            content_type = in_headers.get("HTTP_CONTENT_TYPE", "text/plain").lower()

            if content_type == "text/plain":
                # nothing else to do, just dispatch the request
                self.handle_dispatch()

            elif content_type == "application/x-www-form-urlencoded":
                # request contains encoded content
                try:
                    content_length = int(in_headers["HTTP_CONTENT_LENGTH"])

                except:
                    # length required
                    self._server._error_actions[HTTP_411][1].get(self)

                    return

                # parse content
                self.read_length(content_length, self.handle_urlencoded_content)

            elif content_type.startswith("multipart/form-data"):
                # request contains multipart content
                self._multipart_boundary = "--" + content_type[30:]

                self.read_length(len(self._multipart_boundary), self.handle_multipart_boundary)

        except:
            # bad request
            self._server._error_actions[HTTP_400][1].get(self)

    # ------------------------------------------------------------------------------------------------------------------

    def handle_max_bytes (self, max_bytes):
        """
        This callback will be executed when a maximum byte limit has been met.

        @param max_bytes (int) The maximum byte limit.

        @return (bool) True, if processing should continue, otherwise False.
        """

        # bad request
        self._server._error_actions[HTTP_400][1].get(self)

    # ------------------------------------------------------------------------------------------------------------------

    def handle_multipart_boundary (self, data):
        """
        This callback is executed when a multipart boundary has been located.

        @param data The multipart boundary.
        """

        self.read_length(2, self.handle_multipart_post_boundary)

    # ------------------------------------------------------------------------------------------------------------------

    def handle_multipart_headers (self, data):
        """
        This callback is executed when multipart headers need to be parsed.

        @param data The data that has tentatively been found as multipart headers.
        """

        try:
            # parse headers
            headers = {}

            for header in data.rstrip().split("\r\n"):
                header = header.split(": ")

                headers[header[0].upper()] = header[1]

            disposition = headers["CONTENT-DISPOSITION"][11:]
            name        = disposition[6:disposition.find("\"", 6)].decode("utf-8")
            pos         = disposition.find("filename=\"")

            self.read_delimiter  = self.multipart_read_delimiter
            self._multipart_name = name

            if pos == -1:
                # regular field
                self.read_delimiter(self._multipart_boundary, self.handle_multipart_post_boundary, 1000)

                return

            # file upload
            pos += 10

            if not self.files:
                self.files = {}

            # enlarge the read size so uploads are quicker
            content_length = int(self.in_headers.get("HTTP_CONTENT_LENGTH", 0))

            if content_length >= 1048576:
                # content is at least a meg, use a rather large read size
                self._orig_read_size = self._read_size
                self._read_size      = 131070

            else:
                # content is potentially large, use a moderate read size
                self._orig_read_size = self._read_size
                self._read_size      = 65535

            # open a temp file to store the upload
            chars     = "".join((string.letters, string.digits))
            temp_name = "/".join((self._server._upload_dir, "".join([random.choice(chars) for x in xrange(0, 25)])))

            file = { "error":      None,
                     "filename":   disposition[pos:disposition.find("\"", pos)],
                     "size":       0,
                     "temp_name":  temp_name }

            # add temp filename to list
            self.__files.append(temp_name)

            # determine mimetype
            mimetype = mimetypes.guess_type(file["filename"])

            if mimetype[0]:
                file["content_type"] = mimetype[0]

            elif mimetype[1]:
                file["content_type"] = "+".join(("text/", mimetype[1]))

            else:
                file["content_type"] = "text/plain"

            if name in self.files:
                if type(self.files[name]) != list:
                    # convert individual file to list
                    self.files[name] = [self.files[name]]

                self.files[name].append(file)

            else:
                self.files[name] = file

            self._is_multipart_maxed  = False
            self._multipart_file      = open(temp_name, "wb+")
            self._multipart_file_size = 0

            self.read_delimiter(self._multipart_boundary, self.handle_multipart_post_boundary)

        except:
            # bad request
            self._server._error_actions[HTTP_400][1].get(self)

    # ------------------------------------------------------------------------------------------------------------------

    def handle_multipart_post_boundary (self, data):
        """
        This callback is executed when a multipart post boundary has been located.

        @param data The multipart post boundary.
        """

        if data == "\r\n":
            # there is more multipart data to parse
            self.read_delimiter("\r\n\r\n", self.handle_multipart_headers)

            return

        elif data == "--":
            # no more multipart data
            self.handle_dispatch()

            return

        # bad request
        self._server._error_actions[HTTP_400][1].get(self)

    # ------------------------------------------------------------------------------------------------------------------

    def handle_request (self, data):
        """
        This callback is executed when the initial request line need to be parsed.

        @param data The data that has tentatively been found as the request line.
        """

        self.__files            = []
        self._multipart_file    = None
        self._persistence_type  = None
        self._request_count    += 1
        self._static_file       = None
        self.content_type       = "text/html"
        self.files              = None
        self.in_cookies         = {}
        self.out_cookies        = {}
        self.out_headers        = {}
        self.read_delimiter     = self._orig_read_delimiter
        self.response_code      = HTTP_200

        # parse method, uri and protocol
        try:
            data                  = data.rstrip()
            method, uri, protocol = data.split(" ")

        except:
            try:
                method, uri = data.split(" ")
                protocol    = "HTTP/1.0"

            except:
                # bad request
                self._server._error_actions[HTTP_400][1].get(self)

                return

        # verify method and protocol
        method   = method.upper()
        protocol = protocol.upper()

        if method not in ("CONNECT", "DELETE", "GET", "HEAD", "OPTIONS", "POST", "PUT", "TRACE"):
            # method not allowed
            self._server._error_actions[HTTP_405][1].get(self)

            return

        if protocol not in ("HTTP/1.0", "HTTP/1.1"):
            # http protocol not supported
            self._server._error_actions[HTTP_505][1].get(self)

            return

        # initialize headers
        in_headers = { "HTTP_CONTENT_TYPE": "text/plain",
                       "REMOTE_ADDR":       self._client_address[0],
                       "REMOTE_PORT":       self._client_address[1],
                       "REQUEST_METHOD":    method.upper(),
                       "REQUEST_URI":       uri,
                       "SCRIPT_NAME":       uri,
                       "SERVER_ADDR":       self._server_address[0],
                       "SERVER_PORT":       self._server_address[1],
                       "SERVER_PROTOCOL":   protocol }

        # parse querystring
        pos = uri.find("?")

        if pos > -1:
            query_string               = uri[pos + 1:]
            params                     = urlparse.parse_qs(query_string, True)
            in_headers["QUERY_STRING"] = query_string
            in_headers["SCRIPT_NAME"]  = uri[:pos]

            for key, value in params.items():
                if len(value) == 1:
                    params[key] = value[0]

            self.params = params

        else:
            self.params = {}

        self.in_headers = in_headers

        # parse headers
        self.read_delimiter("\r\n\r\n", self.handle_headers, self._server._max_headers_length)

    # ------------------------------------------------------------------------------------------------------------------

    def handle_shutdown (self):
        """
        This callback will be executed when this HttpClient instance is shutting down.
        """

        # close the current multipart upload file pointer if one exists
        if self._multipart_file and not self._is_multipart_maxed:
            try:
                self._multipart_file.close()

            except:
                pass

        # delete all temp files
        for file in self.__files:
            try:
                os.unlink(file)

            except:
                pass

        Client.handle_shutdown(self)

    # ------------------------------------------------------------------------------------------------------------------

    def handle_upload_finished (self, file):
        """
        This callback is executed when an upload file has finished.

        @param file (dict) The dict of upload details.

        @return (bool) True, if the upload is ok, otherwise False.
        """

        return True

    # ------------------------------------------------------------------------------------------------------------------

    def handle_urlencoded_content (self, data):
        """
        This callback is executed when urlencoded content is ready to be parsed.

        @param data The content.
        """

        params = self.params

        for key, value in urlparse.parse_qs(data.rstrip()).items():
            if key in params:
                values = params[key]

                if type(values) == list:
                    values.extend(value)

                    continue

                values      = [values]
                params[key] = values

                values.extend(value)

            else:
                if len(value) == 1:
                    # individual param value, so let's extract it out of the list
                    params[key] = value[0]

                    continue

                params[key] = value

        # dispatch the client
        self.handle_dispatch()

    # ------------------------------------------------------------------------------------------------------------------

    def handle_write_finished (self):
        """
        This callback will be executed when the entire write buffer has been written.
        """

        if self._static_file:
            # serving a static file
            data = self._static_file.read(FILE_READ_SIZE)

            if len(data) > 0:
                # more data to write
                self.write(data)
                self.flush()

                return

            # finished reading file
            self._static_file.close()

            self._static_file = None

            self.clear_events()

        else:
            if self._is_allowing_persistence and self._persistence_type:
                # allowing another request
                self.clear_write_buffer()
                self.read_delimiter("\r\n", self.handle_request, self._server._max_request_length)

                return

            # clear the events so the server inits the shutdown sequence
            self.clear_events()

    # ------------------------------------------------------------------------------------------------------------------

    def multipart_read_delimiter (self, delimiter, callback, max_bytes=0):
        """
        Read until a certain delimiter has been found within the multipart read buffer.

        @param delimiter (str)    The delimiter to find.
        @param callback  (method) The callback to execute once the delimiter has been found.
        @param max_bytes (int)    The maximum byte limit to read.
        """

        buffer         = self._read_buffer
        data           = buffer.getvalue()
        multipart_file = self._multipart_file
        multipart_name = self._multipart_name
        params         = self.params
        pos            = data.find(delimiter)

        if not multipart_file:
            # form field
            if pos > -1:
                # boundary has been found
                if multipart_name in params:
                    if type(params[multipart_name]) != list:
                        # param already existed, but wasn't a list so let's convert it
                        params[multipart_name] = [params[multipart_name]]

                    params[multipart_name].append(data[:pos - 2])

                else:
                    params[multipart_name] = data[:pos - 2]

                self.read_delimiter = self._orig_read_delimiter

                buffer.truncate(0)
                buffer.write(data[pos + len(delimiter):])

                self.read_length(2, callback)

                return

        else:
            # file upload
            file = self.files[multipart_name]

            if type(file) == list:
                file = file[-1]

            if pos > -1:
                # boundary has been found, write the buffer minus 2 bytes (for \r\n) to the file
                self._multipart_file = None
                self.read_delimiter  = self._orig_read_delimiter

                chunk = data[:pos - 2]

                if not self._is_multipart_maxed:
                    # flush end contents
                    multipart_file.write(chunk)
                    multipart_file.flush()
                    multipart_file.close()

                    self._read_size = self._orig_read_size

                    self._multipart_file_size += len(chunk)

                    if self._server._max_upload_size and self._server._max_upload_size < self._multipart_file_size:
                        # upload is too big
                        file["error"] = ERROR_UPLOAD_MAX_SIZE

                buffer.truncate(0)
                buffer.write(data[pos + len(delimiter):])

                file["size"] = os.stat(file["temp_name"]).st_size

                self.handle_upload_finished(file)

                self.read_length(2, callback)

                return

            # boundary has not been found
            if len(data) >= self._server._upload_buffer_size:
                # flush the buffer to file
                chunk = data[:-len(delimiter)]

                self._multipart_file_size += len(chunk)

                if not self._is_multipart_maxed:
                    multipart_file.write(chunk)
                    multipart_file.flush()

                buffer.truncate(0)
                buffer.write(data[len(data) - len(delimiter):])

                # check file size limit
                if self._server._max_upload_size and self._server._max_upload_size < self._multipart_file_size and \
                   not self._is_multipart_maxed:
                    # upload is too big
                    multipart_file.close()

                    file["error"]            = ERROR_UPLOAD_MAX_SIZE
                    self._is_multipart_maxed = True

        self._read_callback  = callback
        self._read_delimiter = delimiter
        self._read_max_bytes = max_bytes

    # ------------------------------------------------------------------------------------------------------------------

    def set_cookie (self, name, value="", expires=None, path="/", domain=None, http_only=False, secure=False):
        """
        Set a cookie.

        @param name      (str)      The cookie name.
        @param value     (str)      The cookie value.
        @param expires   (datetime) The date and time at which the cookie will expire.
        @param path      (str)      The root path under which the cookie will be valid.
        @param domain    (str)      The domain under which the cookie will be valid.
        @param http_only (bool)     Indicates that the cookie will not be accessible from client script.
        @param secure    (bool)     Indicates that the cookie will only be transmitted over an HTTPS connection.
        """

        cookie = name + "=" + urllib.quote(str(value)) + "; path=" + path

        if domain:
            cookie += "; domain=" + domain

        if expires:
            cookie += "; expires=" + datetime.datetime.fromtimestamp(time.time() + expires) \
                                             .strftime("%A, %d %B %Y %H:%M:%S GMT" + self._server._gmt_offset)

        if http_only:
            cookie += "; HttpOnly"

        if secure:
            cookie += "; secure"

        self.out_cookies[name] = cookie

    # ------------------------------------------------------------------------------------------------------------------

    def serve_static_file (self, path, filename=None):
        """
        Serve a static file.

        @param path     (str) The absolute filesystem path to the file.
        @param filename (str) A substitute download filename.

        @return (bool) True, if the file will be served, otherwise False.
        """

        try:
            file = open(path, "rb")

            self._static_file = file

            if not filename:
                filename = os.path.basename(path)

            self.out_headers["Content-Disposition"] = "attachment; filename=%s" % filename

            # determine mimetype
            mimetype = mimetypes.guess_type(path)

            if mimetype[0]:
                self.content_type = mimetype[0]

            elif mimetype[1]:
                self.content_type = "+".join(("text/", mimetype[1]))

            else:
                self.content_type = "text/plain"

            # compose headers and write the first portion of the file
            self.compose_headers()
            self.write(file.read(FILE_READ_SIZE))
            self.flush()

            return True

        except:
            # file doesn't exist or permission denied
            return False

# ----------------------------------------------------------------------------------------------------------------------

class HttpServer (Server):

    def __init__ (self, gmt_offset="-5", upload_dir="/tmp", upload_buffer_size=50000, max_upload_size=None,
                  max_request_length=5000, max_headers_length=10000, **kwargs):
        """
        Create a new HttpServer instance.

        @param gmt_offset         (str) The GMT offset of the server.
        @param upload_dir         (str) The absolute filesystem path to the directory where uploaded files will be
                                        placed.
        @param upload_buffer_size (int) The upload buffer size.
        @param max_upload_size    (int) The maximum file upload size.
        @param max_request_length (int) The maximum length of the initial request line.
        @param max_headers_length (int) The maximum length for the headers.
        """

        Server.__init__(self, **kwargs)

        self._gmt_offset         = gmt_offset
        self._max_headers_length = max_headers_length
        self._max_request_length = max_request_length
        self._max_upload_size    = max_upload_size
        self._upload_buffer_size = upload_buffer_size
        self._upload_dir         = upload_dir

        # error actions
        self._error_actions = { HTTP_400: (None, HttpAction(self, "400 Bad Request", HTTP_400)),
                                HTTP_401: (None, HttpAction(self, "401 Unauthorized", HTTP_401)),
                                HTTP_402: (None, HttpAction(self, "402 Payment Required", HTTP_402)),
                                HTTP_403: (None, HttpAction(self, "403 Forbidden", HTTP_403)),
                                HTTP_404: (None, HttpAction(self, "404 Not Found", HTTP_404)),
                                HTTP_405: (None, HttpAction(self, "405 Method Not Allowed", HTTP_405)),
                                HTTP_406: (None, HttpAction(self, "406 Not Acceptable", HTTP_406)),
                                HTTP_407: (None, HttpAction(self, "407 Proxy Authentication Required", HTTP_407)),
                                HTTP_408: (None, HttpAction(self, "408 Request Timeout", HTTP_408)),
                                HTTP_409: (None, HttpAction(self, "409 Conflict", HTTP_409)),
                                HTTP_410: (None, HttpAction(self, "410 Gone", HTTP_410)),
                                HTTP_411: (None, HttpAction(self, "411 Length Required", HTTP_411)),
                                HTTP_412: (None, HttpAction(self, "412 Precondition Failed", HTTP_412)),
                                HTTP_413: (None, HttpAction(self, "413 Request Entity Too Large", HTTP_413)),
                                HTTP_414: (None, HttpAction(self, "414 Request-URI Too Long", HTTP_414)),
                                HTTP_415: (None, HttpAction(self, "415 Unsupported Media Type", HTTP_415)),
                                HTTP_416: (None, HttpAction(self, "416 Requested Range Not Satisfiable", HTTP_416)),
                                HTTP_417: (None, HttpAction(self, "417 Expectation Failed", HTTP_417)),
                                HTTP_422: (None, HttpAction(self, "422 Unprocessable Entity", HTTP_422)),
                                HTTP_423: (None, HttpAction(self, "423 Locked", HTTP_423)),
                                HTTP_424: (None, HttpAction(self, "424 Failed Dependency", HTTP_424)),
                                HTTP_426: (None, HttpAction(self, "426 Upgrade Required", HTTP_426)),
                                HTTP_500: (None, HttpAction(self, "500 Internal Server Error", HTTP_500)),
                                HTTP_501: (None, HttpAction(self, "501 Not Implemented", HTTP_501)),
                                HTTP_502: (None, HttpAction(self, "502 Bad Gateway", HTTP_502)),
                                HTTP_503: (None, HttpAction(self, "503 Service Unavailable", HTTP_503)),
                                HTTP_504: (None, HttpAction(self, "504 Gateway Timeout", HTTP_504)),
                                HTTP_505: (None, HttpAction(self, "505 HTTP Version Not Supported", HTTP_505)),
                                HTTP_506: (None, HttpAction(self, "506 Variant Also Negotiates", HTTP_506)),
                                HTTP_507: (None, HttpAction(self, "507 Insufficient Storage", HTTP_507)),
                                HTTP_510: (None, HttpAction(self, "510 Not Extended", HTTP_510)) }

    # ------------------------------------------------------------------------------------------------------------------

    def handle_client (self, client_socket, client_address, server_address):
        """
        Register a new HttpClient instance.

        @param client_socket  (socket) The client socket.
        @param client_address (tuple)  A two-part tuple containing the client ip and port.
        @param server_address (tuple)  A two-part tuple containing the server ip and port to which the client has
                                       made a connection.
        """

        raise ServerException("HttpServer.handle_client() must be overridden")

    # ------------------------------------------------------------------------------------------------------------------

    def handle_exception (self, exception, client=None):
        """
        This callback is executed when an uncaught exception is found while processing a client.

        @param exception (Exception)  The exception.
        @param client    (HttpClient) The HttpClient instance that was active during the exception.
        """

        Server.handle_exception(self, exception)

        if not client:
            return

        client.clear_write_buffer()

        if isinstance(exception, HttpException):
            client.write("HTTP %s\r\nServer: %s\r\n\r\n<h1>%s</h1>" % (exception[1], elements.APP_NAME, exception[0]))

        else:
            client.write("HTTP 500 Internal Server Error\r\nServer: %s\r\n\r\n<h1>Internal Server Error</h1>" %
                         elements.APP_NAME)

        client.flush()

# ----------------------------------------------------------------------------------------------------------------------

class RoutingHttpClient (HttpClient):

    def handle_dispatch (self):
        """
        This callback is executed when the request has been parsed and needs dispatched to a handler.
        """

        route           = self.in_headers["SCRIPT_NAME"].split(":", 1)
        pattern, action = self._server._routes.get(route[0], self._server._error_actions[HTTP_404])

        if not pattern:
            # route doesn't require validated data
            getattr(action, self.in_headers["REQUEST_METHOD"].lower())(self)

            return

        # check for expected data
        if len(route) == 1:
            # route didn't contain data, so it's automatically invalidated (serve 404 as if the url doesn't exist)
            pattern, action = self._server._error_actions[HTTP_404]

            getattr(action, self.in_headers["REQUEST_METHOD"].lower())(self)

            return

        # update headers to reflect proper route details
        self.in_headers["SCRIPT_NAME"], self.in_headers["SCRIPT_ARGS"] = route

        # validate data
        match = pattern.match(route[1])

        if not match:
            # data did not validate successfully (serve 404 as if the url doesn't exist)
            pattern, action = self._server._error_actions[HTTP_404]

            getattr(action, self.in_headers["REQUEST_METHOD"].lower())(self)

            return

        # data validated successfully
        self.params.update(match.groupdict())

        getattr(action, self.in_headers["REQUEST_METHOD"].lower())(self)

# ----------------------------------------------------------------------------------------------------------------------

class RoutingHttpServer (HttpServer):

    def __init__ (self, routes, **kwargs):
        """
        Create a new RoutingHttpServer instance.

        @param routes (dict) A key->(validation, route) mapping.
        """

        HttpServer.__init__(self, **kwargs)

        self._routes = {}

        if type(routes) != dict:
            raise ServerException("Routes must be an instance of dict")

        # compile routes
        for script_name, details in routes.items():
            if type(script_name) != str:
                raise ServerException("Invalid route")

            if type(details) in (list, tuple):
                if type(details[0]) == str:
                    pattern       = details[0]
                    action        = details[1]
                    action_kwargs = dict()

                    if len(details) == 3:
                        action_kwargs = details[2]

                else:
                    pattern       = None
                    action        = details[0]
                    action_kwargs = dict()

                    if len(details) == 2:
                        action_kwargs = details[1]

                try:
                    if not issubclass(action, HttpAction):
                        raise ServerException("Action for route '%s' must be a sub-class of HttpAction" % script_name)

                except ServerException:
                    raise

                except Exception, e:
                    raise ServerException("Action for route '%s' must be a sub-class of HttpAction" % script_name)

                if pattern:
                    # this route requires a pattern
                    if type(pattern) != str:
                        raise ServerException("Regex pattern for route '%s' must be a string" % script_name)

                    try:
                        # take simplified group names and convert them to regex-style group names
                        for match in re.findall("\((?P<name>[^:]+):(?P<pattern>.*?)\)", pattern, re.I):
                            pattern = pattern.replace("(%s:%s)" % match, "(?P<%s>%s)" % match)

                        pattern = re.compile(pattern)

                    except Exception, e:
                        raise ServerException("Regex pattern error for route '%s': %s" % (script_name, str(e)))

                    try:
                        self._routes[script_name] = (pattern, action(server=self, title="Method Not Supported",
                                                                     response_code=HTTP_405, **action_kwargs))

                    except Exception, e:
                        raise ServerException("Action for route '%s' failed to instantiate: %s" % (script_name,
                                                                                                   str(e)))

                else:
                    # no pattern for this route
                    try:
                        self._routes[script_name] = (None, action(server=self, title="Method Not Supported",
                                                                  response_code=HTTP_405, **action_kwargs))

                    except Exception, e:
                        raise ServerException("Action for route '%s' failed to instantiate: %s" % (script_name, str(e)))

            else:
                raise ServerException("Route details must be a tuple or list for route '%s'" % script_name)

    # ------------------------------------------------------------------------------------------------------------------

    def handle_client (self, client_socket, client_address, server_address):
        """
        Register a new RoutingHttpClient instance.

        @param client_socket  (socket) The client socket.
        @param client_address (tuple)  A two-part tuple containing the client ip and port.
        @param server_address (tuple)  A two-part tuple containing the server ip and port to which the client has
                                       made a connection.
        """

        self.register_client(RoutingHttpClient(client_socket, client_address, self, server_address))

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
            client._server._error_actions[HTTP_404][1].get(client)
