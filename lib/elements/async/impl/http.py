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

PERSISTENCE_KEEP_ALIVE = 1
PERSISTENCE_PROTOCOL   = 2

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
        self.files = None

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
                    raise HttpException("Length Required", HTTP_411)

                # parse content
                self.read_length(content_length, self.handle_urlencoded_content)

            elif content_type.startswith("multipart/form-data"):
                # request contains multipart content
                self._multipart_boundary = "--" + content_type[30:]

                self.read_length(len(self._multipart_boundary), self.handle_multipart_boundary)

        except HttpException:
            raise

        except:
            raise HttpException("Bad Request", HTTP_400)

    # ------------------------------------------------------------------------------------------------------------------

    def handle_max_bytes (self, max_bytes):
        """
        This callback will be executed when a maximum byte limit has been met.

        @param max_bytes (int) The maximum byte limit.

        @return (bool) True, if processing should continue, otherwise False.
        """

        raise HttpException("Bad Request", HTTP_400)

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

            # open a temp file to store the upload
            chars     = "".join((string.letters, string.digits))
            temp_name = "".join([random.choice(chars) for x in xrange(0, 25)])

            file = { "error":      None,
                     "error_code": None,
                     "filename":   disposition[pos:disposition.find("\"", pos)],
                     "size":       0,
                     "temp_name":  temp_name }

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

            self._multipart_file = open("/".join((self._server._upload_dir, temp_name)), "wb+")

            self.read_delimiter(self._multipart_boundary, self.handle_multipart_post_boundary)

        except ElementsException:
            raise

        except:
            raise HttpException("Bad Request", HTTP_400)

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

        raise HttpException("Bad Request", HTTP_400)

    # ------------------------------------------------------------------------------------------------------------------

    def handle_request (self, data):
        """
        This callback is executed when the initial request line need to be parsed.

        @param data The data that has tentatively been found as the request line.
        """

        print "woot"

        self._multipart_file    = None
        self._persistence_type  = None
        self._request_count    += 1
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
                raise HttpException("Bad Request", HTTP_400)

        # verify method and protocol
        protocol = protocol.upper()

        if protocol not in ("HTTP/1.0", "HTTP/1.1"):
            raise HttpException("Bad Request", HTTP_400)

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
        if self._multipart_file:
            try:
                self._multipart_file.close()

            except:
                pass

        # delete all temp files
        if self.files:
            for file in self.files:
                if type(file) != list:
                    file = [file]

                for file in file:
                    try:
                        os.unlink("/".join((self._server._upload_dir, file["temp_name"])))

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

    def handle_upload_flushed (self, file):
        """
        This callback is executed when an upload file has been flushed, but still is not finished.

        @param file (dict) The dict of upload details.

        @return (bool) True, if upload processing should continue, otherwise False.
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

        buffer = self._read_buffer
        data   = buffer.getvalue()
        file   = self._multipart_file
        name   = self._multipart_name
        params = self.params
        pos    = data.find(delimiter)

        if not self._multipart_file:
            # form field
            if pos > -1:
                # boundary has been found
                if name in params:
                    if type(params[name]) != list:
                        # param already existed, but wasn't a list so let's convert it
                        params[name] = [params[name]]

                    params[name].append(data[:pos - 2])

                else:
                    params[self._multipart_name] = data[:pos - 2]

                self.read_delimiter = self._orig_read_delimiter

                buffer.seek(0)
                buffer.truncate()
                buffer.write(data[pos + len(delimiter):])

                self.read_length(2, callback)

                return

        else:
            # file upload
            if pos > -1:
                # boundary has been found, write the buffer minus 2 bytes (for \r\n) to the file
                self._multipart_file = None
                self.read_delimiter  = self._orig_read_delimiter

                file.write(data[:pos - 2])
                file.flush()
                file.close()

                buffer.seek(0)
                buffer.truncate()
                buffer.write(data[pos + len(delimiter):])

                file         = self.files[self._multipart_name][-1]
                file["size"] = os.stat("/".join((self._server._upload_dir, file["temp_name"]))).st_size

                self.handle_upload_finished(file)

                self.read_length(2, callback)

                return

            # boundary has not been found
            if len(data) >= self._server._upload_buffer_size:
                # flush the buffer to file
                file.write(data[:-len(delimiter)])
                file.flush()

                buffer.seek(0)
                buffer.truncate()
                buffer.write(data[len(data) - len(delimiter):])

                self.handle_upload_flushed(self.files[self._multipart_name][-1])

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

# ----------------------------------------------------------------------------------------------------------------------

class HttpServer (Server):

    def __init__ (self, gmt_offset="-5", upload_dir="/tmp", upload_buffer_size=50000, max_request_length=5000,
                  max_headers_length=10000, **kwargs):
        """
        Create a new HttpServer instance.

        @param gmt_offset         (str) The GMT offset of the server.
        @param upload_dir         (str) The absolute filesystem path to the directory where uploaded files will be
                                        placed.
        @param upload_buffer_size (int) The upload buffer size.
        @param max_request_length (int) The maximum length of the initial request line.
        @param max_headers_length (int) The maximum length for the headers.
        """

        Server.__init__(self, **kwargs)

        self._gmt_offset         = gmt_offset
        self._max_headers_length = max_headers_length
        self._max_request_length = max_request_length
        self._upload_buffer_size = upload_buffer_size
        self._upload_dir         = upload_dir

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
