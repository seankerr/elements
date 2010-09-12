# This file is part of Elements.
# Copyright (c) 2010 Sean Kerr. All rights reserved.
#
# The full license is available in the LICENSE file that was distributed with this source code.
#
# Author: Noah Fontes <nfontes@invectorate.com>

try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

import os
import struct

from elements.core.exception import ClientException
from elements.core.exception import ProtocolException

from elements.async.client   import Client
from elements.async.client   import EVENT_READ

from elements.async.server   import Server

# ----------------------------------------------------------------------------------------------------------------------
# PROTOCOL SPECIFICATION AND CONSTANTS
# ----------------------------------------------------------------------------------------------------------------------

FCGI_HEADER_LEN = 8

FCGI_VERSION_1 = 1

FCGI_BEGIN_REQUEST     =  1
FCGI_ABORT_REQUEST     =  2
FCGI_END_REQUEST       =  3
FCGI_PARAMS            =  4
FCGI_STDIN             =  5
FCGI_STDOUT            =  6
FCGI_STDERR            =  7
FCGI_DATA              =  8
FCGI_GET_VALUES        =  9
FCGI_GET_VALUES_RESULT = 10
FCGI_UNKNOWN_TYPE      = 11
FCGI_MAXTYPE           = FCGI_UNKNOWN_TYPE

FCGI_NULL_REQUEST_ID = 0

# ----------------------------------------------------------------------------------------------------------------------

FCGI_KEEP_CONN = 1

FCGI_RESPONDER  = 1
FCGI_AUTHORIZER = 2
FCGI_FILTER     = 3

# ----------------------------------------------------------------------------------------------------------------------

FCGI_REQUEST_COMPLETE = 0
FCGI_CANT_MPX_CONN    = 1
FCGI_OVERLOADED       = 2
FCGI_UNKNOWN_ROLE     = 3

FCGI_MAX_CONNS  = "FCGI_MAX_CONNS"
FCGI_MAX_REQS   = "FCGI_MAX_REQS"
FCGI_MPXS_CONNS = "FCGI_MPXS_CONNS"

# ----------------------------------------------------------------------------------------------------------------------

HEADER_STRUCT           = struct.Struct('>BBHHBx')

BEGIN_REQUEST_STRUCT    = struct.Struct('>HBxxxxx')
END_REQUEST_STRUCT      = struct.Struct('>IBxxx')
UNKNOWN_TYPE_STRUCT     = struct.Struct('>Bxxxxxxx')

SINGLE_INTEGER_STRUCT   = struct.Struct('>I')
NAME_VALUE_PAIR_STRUCTS = { 0x0 | 0x0: struct.Struct('>BB'),
                            0x0 | 0x2: struct.Struct('>BI'),
                            0x1 | 0x0: struct.Struct('>IB'),
                            0x1 | 0x2: struct.Struct('>II') }

# ----------------------------------------------------------------------------------------------------------------------
# RECORD WRITERS
# ----------------------------------------------------------------------------------------------------------------------

class _Record (object):

    def __init__ (self, type, request_id = FCGI_NULL_REQUEST_ID):
        """
        Creates a new writable record object.

        @param type       (int) The FastCGI type for the record.
        @param request_id (int) The request ID that should be sent with this record.
        """

        self._version = FCGI_VERSION_1
        self._type = type
        self._request_id = request_id

    # ------------------------------------------------------------------------------------------------------------------

    def write (self, client):
        """
        Writes the content of this record to the given client's buffer.

        @param client (FastcgiClient) The client to which this record should be written.
        """

        data = self.render()
        data_length = len(data)

        client.write(HEADER_STRUCT.pack(self._version, self._type, self._request_id, data_length, 0))
        client.write(data)

    # ------------------------------------------------------------------------------------------------------------------

    def render (self):
        """
        Creates the record body for this record.

        @return (str) The record body.
        """

        raise NotImplementedError("_Record#render() must be overridden")

# ----------------------------------------------------------------------------------------------------------------------

class _GetValuesResultRecord (_Record):

    def __init__ (self, results):
        """
        Creates a new record representing a result to the FCGI_GET_VALUES record.

        @param results (dict) A dictionary containing names and values to return to the application server.
        """

        _Record.__init__(self, FCGI_GET_VALUES_RESULT)
        self._results = results

    # ------------------------------------------------------------------------------------------------------------------

    def _write_nv_pair (self, name, value, destination):
        """
        Writes a name-value pair to the specified file-like object.

        @param name        (str)  The key to write.
        @param value       (str)  The corresponding value.
        @param destination (file) The object to which the name/value pair should be written.
        """

        name_length  = len(name)
        value_length = len(value)

        flags = 0x0
        if name_length > 127:
            flags       |= 0x1
            name_length |= 0x80000000L

        if value_length > 127:
            flags        |= 0x2
            value_length |= 0x80000000L

        destination.write(NAME_VALUE_PAIR_STRUCTS[flags].pack(name_length, value_length))
        destination.write(name)
        destination.write(value)

    # ------------------------------------------------------------------------------------------------------------------

    def render (self):
        """
        Creates a message body for FCGI_GET_VALUES_RESULT.

        @return (str) The message body.
        """

        buffer = StringIO.StringIO()

        for name, value in self._results.iteritems():
            self._write_nv_pair(name, value, buffer)

        contents = buffer.getvalue()
        buffer.close()

        return buffer

# ----------------------------------------------------------------------------------------------------------------------

class _UnknownTypeRecord (_Record):

    def __init__ (self, unknown_type):
        """
        Creates a new record representing a notification of an unexpected/unknown type received in a management record.

        @param unknown_type (int) The type to which this implementation could not respond.
        """

        _Record.__init__(self, FCGI_UNKNOWN_TYPE)
        self._unknown_type = unknown_type

    # ------------------------------------------------------------------------------------------------------------------

    def render (self):
        """
        Creates a message body for FCGI_UNKNOWN_TYPE.

        @return (str) The message body.
        """

        return UNKNOWN_TYPE_STRUCT.pack(self._unknown_type)

# ----------------------------------------------------------------------------------------------------------------------

class _EndRequestRecord (_Record):

    def __init__ (self, application_status, protocol_status, request_id):
        """
        Creates a new record representing the end of a request (in reality, the end of a response coming from an
        application on this side).

        @param application_status (int) The application result code (like an exit code).
        @param protocol_status    (int) One of the valid protocol-level result codes identifying the reason the request
                                        is terminating.
        @param request_id         (int) The request ID that is being terminated.
        """

        _Record.__init__(self, FCGI_END_REQUEST, request_id)
        self._application_status = application_status
        self._protocol_status    = protocol_status

    # ------------------------------------------------------------------------------------------------------------------

    def render (self):
        """
        Creates a message body for FCGI_END_REQUEST.

        @return (str) The message body.
        """

        return END_REQUEST_STRUCT.pack(self._application_status, self._protocol_status)

# ----------------------------------------------------------------------------------------------------------------------

class _StreamRecord (_Record):

    def __init__ (self, type, data, request_id):
        """
        Creates a new record that represents any streaming data type.

        @param type       (int)    The FastCGI type for the record (must be one of FASTCGI_STDOUT or FASTCGI_STDERR for
                                   our purposes).
        @param data       (object) The data blob to be sent. This implementation sends str(data) as the message body.
        @param request_id (int)    The request ID to which to the data belongs.
        """

        _Record.__init__(self, type, request_id)
        self._data = data

    # ------------------------------------------------------------------------------------------------------------------

    def render (self):
        """
        Creates a message body for the given record type.

        @return (str) The message body.
        """

        return str(self._data)

# ----------------------------------------------------------------------------------------------------------------------
# STDIN/STDOUT WRITER
# ----------------------------------------------------------------------------------------------------------------------

class _OutputWriter (object):
    """
    An _OutputWriter is a small wrapper around _StreamRecord types to make actually writing data to the client more
    intuitive for application-level developers.

    Its API is similar to file objects, although it only implements methods that involve writing.
    """

    def __init__ (self, client, type):
        """
        Creates a new writer for streaming types.

        @param client (FastcgiClient) The client to which data should be written.
        @param type   (int)           The streaming type to use.
        """

        self._client = client
        self._type   = type
        self._reset()

    # ------------------------------------------------------------------------------------------------------------------

    def write (self, data):
        """
        Writes the given data to the client.

        @param data (object) The data to write.
        """

        if not self._closed:
            while len(data) > 0:
                self._client._write_record(_StreamRecord(self._type, data[:65535], self._client.request_id))
                self._has_data = True

                data = data[65535:]

    # ------------------------------------------------------------------------------------------------------------------

    def writelines (self, sequence):
        """
        Writes a sequence of data to the client.

        This method behaves like file#writelines, and does no sanitization/modification of input (so newlines are not
        added, for instance).

        @param sequence (object) An iterable object containing blobs of data to write.
        """

        for data in sequence:
            self.write(data)

    # ------------------------------------------------------------------------------------------------------------------

    def close (self):
        """
        Closes this stream by setting a flag preventing further output.
        """

        self._closed = True

    # ------------------------------------------------------------------------------------------------------------------

    @property
    def closed (self):
        """
        Whether this stream has already been closed.

        @return (bool) True if the stream has been closed; false otherwise.
        """

        return self._closed

    # ------------------------------------------------------------------------------------------------------------------

    def _reset (self):
        """
        Resets this object to a default state so it can be re-used.
        """

        self._closed   = False
        self._has_data = False

# ----------------------------------------------------------------------------------------------------------------------

class FastcgiException (ProtocolException):
    """
    Raised when an unexpected protocol error occurs while handling a FastCGI request.
    """

    pass

# ----------------------------------------------------------------------------------------------------------------------

class FastcgiClient (Client):

    def __init__ (self, client_socket, client_address, server, server_address):
        """
        Creates a new FastcgiClient instance.

        @param client_socket  (socket) The client socket.
        @param client_address (tuple)  A two-part tuple containing the client ip and port.
        @param server         (Server) The Server instance within which this HttpClient is being created.
        @param server_address (tuple)  A two-part tuple containing the server ip and port to which the client has
                                       made a connection.
        """

        Client.__init__(self, client_socket, client_address, server, server_address)

        self._is_allowing_persistence = False                            # whether this client will be allowed to handle
                                                                         # multiple connections
        self._maximum_requests        = None                             # the maximum number of requests this client
                                                                         # will accept
        self._handled_requests        = 0                                # number of requests processed so far
        self._persistence_requested   = True                             # whether the server wants to use persistence
                                                                         # for further requests

        self._header                  = None                             # header data for this request

        self._params_io               = StringIO.StringIO()              # temporary (StringIO) storage for FCGI_PARAMS
        self._has_params              = False                            # whether we've read in all the params

        self.request_id               = FCGI_NULL_REQUEST_ID             # the current FastCGI request ID for this
                                                                         # process
        self.flags                    = None                             # flags associated with the current request
        self.params                   = None                             # input parameters to the current request

        self.stdin                    = StringIO.StringIO()              # FCGI_STDIN
        self._has_stdin               = False                            # whether we've read in stdin completely

        self.stdout                   = _OutputWriter(self, FCGI_STDOUT) # FCGI_STDOUT
        self.stderr                   = _OutputWriter(self, FCGI_STDERR) # FCGI_STDERR

        # get the first record and parse from there
        self._read_record()

    # ------------------------------------------------------------------------------------------------------------------

    def allow_persistence (self, status, max_requests = None):
        """
        Set the persistence status.

        @param status       (bool) The persistence status.
        @param max_requests (int)  The maximum persistent requests to serve before the connection will be closed.
        """

        self._is_allowing_persistence = status
        self._maximum_requests        = max_requests

    # ------------------------------------------------------------------------------------------------------------------

    def _read_nv_pairs (self, data, data_length):
        """
        Reads a sequence of name-value pairs from a data blob.

        @param data        (str) The string from which name-value pairs should be read.
        @param data_length (int) The length of the data.

        @return (dict) A dictionary containing the name-value pairs from the input string.
        """

        # section 3.4 of the protocol might be one of the most retarded things I have ever seen in my life
        pairs = {}

        v  = 0
        nl = 0 # declare in the outer scope for performance
        vl = 0
        while v < data_length:
            nl = ord(data[v])
            if nl & 0x80:
                nl = SINGLE_INTEGER_STRUCT.unpack(data[v:(v + 4)])[0] & 0x7fffffff
                v += 3

            vl = ord(data[v + 1])
            if vl & 0x80:
                vl = SINGLE_INTEGER_STRUCT.unpack(data[v:(v + 4)])[0] & 0x7fffffff
                v += 3

            pairs[data[(v + 2):(v + 2 + nl)]] = data[(v + 2 + nl):(v + 2 + nl + vl)]
            v += 2 + nl + vl

        return pairs

    # ------------------------------------------------------------------------------------------------------------------

    def _handle_record_get_values (self, header, data):
        """
        Handles a request for FCGI_GET_VALUES and sends a FCGI_GET_VALUES_RESULT response.

        @param header (dict) The decoded header data.
        @param data   (str)  A blob of name-value pairs (with empty values) containing implementation-level values to
                             decode.
        """

        requests  = self._read_nv_pairs(data, len(data))
        responses = {}

        for key in requests.keys():
            if key == FCGI_MAX_CONNS or key == FCGI_MAX_REQS:
                responses[key] = str(self._server.worker_count)

            elif key == FCGI_MPXS_CONNS:
                responses[key] = "1" if self._is_allowing_persistence else "0"

        self._write_record_and_flush(_GetValuesResultRecord(responses))

    # ------------------------------------------------------------------------------------------------------------------

    def _handle_record_unknown_type (self, header):
        """
        Handles any unknown management record type and sends an FCGI_UNKNOWN_TYPE response.

        @param header (dict) The decoded header data.
        """

        unknown_type = header["type"]
        self._write_record_and_flush(_UnknownTypeRecord(unknown_type))

    # ------------------------------------------------------------------------------------------------------------------

    def handle_dispatch (self):
        """
        Callback raised when a request is ready to be processed by the client.
        """

        raise ClientException("FastcgiClient#handle_dispatch() must be overriden")

    # ------------------------------------------------------------------------------------------------------------------

    def _maybe_dispatch (self):
        """
        Dispatches the current request if the server has completed sending FCGI_PARAMS and FCGI_STDIN records, otherwise
        requests the next record.
        """

        # need both params and stdin to dispatch a request
        if self._has_params and self._has_stdin:
            self.params = self._read_nv_pairs(self._params_io.getvalue(), self._params_io.tell())

            self.stdin.seek(0)

            self._params_io.truncate(0)
            self._has_params = False

            status = self.handle_dispatch()

            self.stdin.truncate(0)
            self._has_stdin = False

            self._write_record(_EndRequestRecord(0 if status is None else status, FCGI_REQUEST_COMPLETE, self.request_id))

            # flush everything at the end of the request; this can result in the connection closing
            self.flush()

        else:
            self._read_record()

    # ------------------------------------------------------------------------------------------------------------------

    def _handle_record_begin_request (self, header, data):
        """
        Handles a request to begin a new request and requests the next record upon completion.

        @param header (dict) The decoded header data.
        @param data   (str)  Undecoded data containing the role to be used (currently only FCGI_RESPONDER is supported)
                             and any additional request flags.
        """

        request_id = header["request_id"]
        
        if self.request_id:
            # we're already executing a request, so cancel this one
            self._write_record_and_flush(_EndRequestRecord(0, FCGI_CANT_MPX_CONN))

        self.request_id = request_id

        (role, flags) = BEGIN_REQUEST_STRUCT.unpack(data)

        # do we want to keep persistence enabled?
        if flags & FCGI_KEEP_CONN == 0 or (self._maximum_requests and self._handled_requests == self._maximum_requests):
            self._persistence_requested = False

        elif self._maximum_requests and self._handled_requests > self._maximum_requests:
            self._persistence_requested = False
            self._write_record_and_flush(_EndRequestRecord(0, FCGI_OVERLOADED, request_id))
            return

        if role == FCGI_RESPONDER:
            self.flags = flags
            self._has_params = False
            self._has_stdin  = False

            # reset stdout and stderr
            self.stdout._reset()
            self.stderr._reset()

            self._handled_requests += 1

            self._read_record()

        else:
            self._write_record_and_flush(_EndRequestRecord(0, FCGI_UNKNOWN_ROLE, request_id))

    # ------------------------------------------------------------------------------------------------------------------

    def _handle_record_abort_request (self, header, data):
        """
        Handles a request to abort a given request. Since we execute requests serially, this method is a no-op.

        @param header (dict) The decoded header data.
        @param data   (str)  An empty string.
        """

        self._read_record()

    # ------------------------------------------------------------------------------------------------------------------

    def _handle_record_params (self, header, data):
        """
        Handles an FCGI_PARAMS record by appending data to the current parameter string and tries to dispatch the
        request using FastcgiClient#_maybe_dispatch() upon completion.

        @param header (dict) The decoded header data.
        @param data   (str)  A partial representation of the parameters to this request.
        """

        request_id = header["request_id"]

        if request_id != self.request_id:
            return

        if header["content_length"] == 0:
            self._has_params = True

        else:
            self._params_io.write(data)

        self._maybe_dispatch()

    # ------------------------------------------------------------------------------------------------------------------

    def _handle_record_stdin (self, header, data):
        """
        Handles an FCGI_STDIN record by appending data to the current stdin string and tries to dispatch the request
        using FastcgiClient#_maybe_dispatch() upon completion.

        @param header (dict) The decoded header data.
        @param data   (str)  A partial representation of the input to this request, normally a POST or PUT body.
        """

        request_id = header["request_id"]

        if request_id != self.request_id:
            return

        if header["content_length"] == 0:
            self._has_stdin = True

        else:
            self.stdin.write(data)

        self._maybe_dispatch()

    # ------------------------------------------------------------------------------------------------------------------

    def _handle_record (self, data):
        """
        Handles a record body after headers have been decoded. If the requested record is a management record, this
        method requests the next record from the client.

        @param data   (str)  The message body.
        """

        header = self._header
        data   = data[:header["content_length"]]

        if header["request_id"] == FCGI_NULL_REQUEST_ID:
            # management records
            if header["type"] == FCGI_GET_VALUES:
                self._handle_record_get_values(header, data)

            else:
                self._handle_record_unknown_type(header)

            self._read_record()

        else:
            # request headers
            if header["type"] == FCGI_BEGIN_REQUEST:
                self._handle_record_begin_request(header, data)

            elif header["type"] == FCGI_ABORT_REQUEST:
                self._handle_record_abort_request(header, data)

            elif header["type"] == FCGI_PARAMS:
                self._handle_record_params(header, data)

            elif header["type"] == FCGI_STDIN:
                self._handle_record_stdin(header, data)

            elif header["type"] == FCGI_DATA:
                # there's a fairly good chance that we've already dispatched the request by the time we receive this, so
                # we just won't support it
                pass

            else:
                raise FastcgiException("Unexpected record type %d while trying to handle request", header["type"])

    # ------------------------------------------------------------------------------------------------------------------

    def _handle_record_header (self, data):
        """
        Decodes a record header and then attempts to read the length of the content and padding.

        @param data (str) The undecoded header data blob.
        """

        (version, type, request_id, content_length, padding_length) = HEADER_STRUCT.unpack(data)

        if version != FCGI_VERSION_1:
            raise ClientException("Invalid FastCGI version received in header: %d" % version)

        self._header = { "type":           type,
                         "request_id":     request_id,
                         "content_length": content_length }

        self.read_length(content_length + padding_length, self._handle_record)

    # ------------------------------------------------------------------------------------------------------------------

    def _read_record (self):
        """
        Requests the event handler to read the next record from the data stream.
        """

        self.read_length(FCGI_HEADER_LEN, self._handle_record_header)

    # ------------------------------------------------------------------------------------------------------------------

    def _write_record (self, record):
        """
        Writes a given record to this client's data stream by invoking the _Record#write() method on the record.

        Upon completion, this method checks whether the record is an _EndRequestRecord, and if so determines whether
        this client should accept more connections or whether it is in a finalization state and acts accordingly.

        @param record (_Record) The record to write.
        """

        record.write(self)

        if isinstance(record, _EndRequestRecord):
            self.request_id = FCGI_NULL_REQUEST_ID

            if self._is_allowing_persistence and self._persistence_requested:
                self.clear_write_buffer()
                self._read_record()

            else:
                self._events &= ~EVENT_READ

    # ------------------------------------------------------------------------------------------------------------------

    def _write_record_and_flush (self, record):
        """
        Utility method to write a method and immediately flush the data stream afterwards.

        @param record (_Record) The record to write.
        """

        self._write_record(record)
        self.flush()

    # ------------------------------------------------------------------------------------------------------------------

    def handle_write_finished (self):
        """
        Callback invoked when the full client write buffer has actually been written to the client's stream. Clears all
        further events if the client is no longer reading.
        """

        # if we're no longer reading events, and we just flushed the write buffer, then clear all events so the socket
        # shuts down
        if self._events & EVENT_READ == 0:
            self.clear_events()

# ----------------------------------------------------------------------------------------------------------------------

class FastcgiServer (Server):

    def __init__ (self, **kwargs):
        """
        Creates a new FastcgiServer instance.
        """

        Server.__init__(self, **kwargs)

    # ------------------------------------------------------------------------------------------------------------------

    def handle_client (self, client_socket, client_address, server_address):
        """
        Registers a new FastcgiClient instance.

        @param client_socket  (socket) The client socket.
        @param client_address (tuple)  A two-part tuple containing the client ip and port.
        @param server_address (tuple)  A two-part tuple containing the server ip and port to which the client has
                                       made a connection.
        """

        raise NotImplementedError("FastcgiServer#handle_client() must be overridden")

    # ------------------------------------------------------------------------------------------------------------------

    def handle_exception (self, exception, client = None):
        """
        Handles an unexpected exception that occurs during client processing.

        @param exception (Exception)     The exception raised.
        @param client    (FastcgiClient) The client instance that generated the exception.
        """

        Server.handle_exception(self, exception, client)

        if not client or not client.request_id:
            return

        client._write_record(_StreamRecord(FCGI_STDERR, "Could not process request: Internal error", client.request_id))
        client._write_record_and_flush(_EndRequestRecord(1, FCGI_REQUEST_COMPLETE, client.request_id))
