# This file is part of Elements.
# Copyright (c) 2010 Sean Kerr. All rights reserved.
#
# The full license is available in the LICENSE file that was distributed with this source code.
#
# Author: Sean Kerr <sean@code-box.org>

try:
    import cStringIO as StringIO
except:
    import StringIO

try:
    from fcntl import fcntl   as fcntl_func
    from fcntl import F_GETFL as fcntl_getfl
    from fcntl import F_SETFL as fcntl_setfl

except:
    from win32_support import fcntl   as fcntl_func
    from win32_support import F_GETFL as fcntl_getfl
    from win32_support import F_SETFL as fcntl_setfl

import os
import socket
import time

from os import O_NONBLOCK as o_nonblock

from elements.core.exception import ChannelException
from elements.core.exception import ClientException

# ----------------------------------------------------------------------------------------------------------------------

EVENT_READ  = 0
EVENT_WRITE = 0

# ----------------------------------------------------------------------------------------------------------------------

class Client:

    def __init__ (self, client_socket, client_address, server, server_address):
        """
        Create a new Client instance.

        @param client_socket  (socket) The client socket.
        @param client_address (tuple)  A two-part tuple containing the client ip and port.
        @param server         (Server) The Server instance within which this Client is being created.
        @param server_address (tuple)  A two-part tuple containing the server ip and port to which the client has
                                       made a connection.
        """

        self._client_address   = client_address         # client address
        self._client_socket    = client_socket          # client ip
        self._events           = 0                      # active events
        self._fileno           = client_socket.fileno() # file descriptor
        self._is_channel       = False                  # indicates that this client is a channel
        self._is_host          = False                  # indicates that this client is a host
        self._last_access_time = time.time()            # last access time for this client
        self._read_buffer      = StringIO.StringIO()    # incoming data buffer
        self._read_callback    = None                   # method to execute on the occurence of a read event
        self._read_delimiter   = None                   # needle to find in the incoming data buffer
        self._read_length      = None                   # length of data to read
        self._read_max_bytes   = None                   # maximum read buffer length when using read_delimiter()
        self._read_size        = 4096                   # maximum bytes to read from the client socket
        self._server           = server                 # server instance
        self._server_address   = server_address         # server address
        self._write_buffer     = StringIO.StringIO()    # outgoing data buffer
        self._write_index      = 0                      # write buffer index

        # disable blocking
        fcntl_func(self._fileno, fcntl_setfl, fcntl_func(self._fileno, fcntl_getfl) | o_nonblock)

    # ------------------------------------------------------------------------------------------------------------------

    def clear (self):
        """
        Clear the write buffer.
        """

        self._write_buffer.seek(0)
        self._write_buffer.truncate()

        self._write_index = 0

    # ------------------------------------------------------------------------------------------------------------------

    def flush (self):
        """
        Notify the event manager that there is write data available.
        """

        self._events |= EVENT_WRITE

    # ------------------------------------------------------------------------------------------------------------------

    def handle_error (self):
        """
        This callback will be executed when a read/write error has occurred.
        """

        pass

    # ------------------------------------------------------------------------------------------------------------------

    def handle_max_bytes (self, max_bytes):
        """
        This callback will be executed when a maximum byte limit has been met.

        @param max_bytes (int) The maximum byte limit.

        @return (bool) True, if processing should continue, otherwise False.
        """

        return False

    # ------------------------------------------------------------------------------------------------------------------

    def handle_read (self):
        """
        This callback will be executed when read data is available.
        """

        data = self._client_socket.recv(self._read_size)

        if len(data) == 0:
            # the client closed the connection
            self._events = 0

            return

        self._read_buffer.write(data)

        if self._read_delimiter:
            self.read_delimiter(self._read_delimiter, self._read_callback, self._read_max_bytes)

        elif self._read_length:
            self.read_length(self._read_length, self._read_callback)

    # ------------------------------------------------------------------------------------------------------------------

    def handle_shutdown (self):
        """
        This callback will be executed when this Client instance is shutting down.
        """

        try:
            self._client_socket.close()

        except:
            pass

    # ------------------------------------------------------------------------------------------------------------------

    def handle_timeout (self, timeout):
        """
        This callback will be executed when this Client instance has been idle too long.

        @param timeout (int) The timeout.

        @return (bool) True, if processing should continue, otherwise False.
        """

        return False

    # ------------------------------------------------------------------------------------------------------------------

    def handle_write (self):
        """
        This callback will be executed when write data is available.
        """

        buffer = self._write_buffer
        data   = buffer.getvalue()
        length = self._client_socket.send(data[self._write_index:])

        if length == len(data):
            # write buffer has been entirely written
            self._events &= ~EVENT_WRITE
            
            self.handle_write_finished()

            return

        # there is more data to write
        # note: we speed up small writes by eliminating the seek/truncate/write on every call
        self._write_index += length

        if len(data) > 65535:
            buffer.seek(0)
            buffer.truncate()
            buffer.write(data[self._write_index:])
            
            self._write_index = 0

    # ------------------------------------------------------------------------------------------------------------------

    def handle_write_finished (self):
        """
        This callback will be executed when the entire write buffer has been written.
        """

        pass

    # ------------------------------------------------------------------------------------------------------------------

    def read_delimiter (self, delimiter, callback, max_bytes=0):
        """
        Read until a certain delimiter has been found within the read buffer.

        @param delimiter (str)    The delimiter to find.
        @param callback  (method) The callback to execute once the delimiter has been found.
        @param max_bytes (int)    The maximum byte limit to read.
        """

        buffer = self._read_buffer
        data   = buffer.getvalue()
        pos    = data.find(delimiter)

        if pos > -1:
            # the delimiter has been found
            if max_bytes and pos > max_bytes:
                # the maximum byte limit has been reached
                self._events &= ~EVENT_READ 

                if not self.handle_max_bytes(max_bytes):
                    # max bytes callback has stopped client processing
                    return

            pos += len(delimiter)

            self._events &= ~EVENT_READ

            buffer.seek(0)
            buffer.truncate()
            buffer.write(data[pos:])

            callback(data[:pos])

            return

        # the delimiter still hasn't been sent
        if max_bytes and len(data) >= max_bytes:
            # the maximum byte limit has been reached
            self._events &= ~EVENT_READ 

            if not self.handle_max_bytes(max_bytes):
                # max bytes callback has stopped client processing
                return

            max_bytes = None

        self._events         |= EVENT_READ
        self._read_callback   = callback
        self._read_delimiter  = delimiter
        self._read_max_bytes  = max_bytes

    # ------------------------------------------------------------------------------------------------------------------

    def read_length (self, length, callback):
        """
        Read a certain length of data.

        @param length   (int)    The length to read.
        @param callback (method) The callback to execute once the length has been read entirely.
        """

        buffer = self._read_buffer
        data   = buffer.getvalue()
        
        if len(data) >= length:
            # the read buffer has met our length requirement
            self._events &= ~EVENT_READ

            buffer.seek(0)
            buffer.truncate()
            buffer.write(data[length:])

            callback(data[:length])

            return

        # there is still more to read
        self._events        |= EVENT_READ
        self._read_callback  = callback
        self._read_length    = length

    # ------------------------------------------------------------------------------------------------------------------

    def write (self, data):
        """
        Append data onto the write buffer.
        """

        self._write_buffer.write(data)

# ----------------------------------------------------------------------------------------------------------------------

class ChannelClient (Client):

    def __init__ (self, socket, pid, server):
        """
        Create a new ChannelClient instance.

        @param socket (socket) The channel socket.
        @param pid    (int)    The process id.
        @param server (Server) The Server instance within which this ChannelClient is being created.
        """

        Client.__init__(self, socket, None, server, None)

        self._is_blocking = False
        self._pid         = pid

# ----------------------------------------------------------------------------------------------------------------------

class BlockingChannelClient (ChannelClient):

    def __init__ (self, socket, pid, server):
        """
        Create a new BlockingChannelClient instance.

        @param socket (socket) The channel socket.
        @param pid    (int)    The process id.
        @param server (Server) The Server instance within which this BlockingChannelClient is being created.
        """

        ChannelClient.__init__(self, socket, pid, server)

        self._is_blocking = True

        # re-enable blocking
        fcntl_func(socket.fileno(), fcntl_setfl, fcntl_func(socket.fileno(), fcntl_getfl) & ~o_nonblock)

    # ------------------------------------------------------------------------------------------------------------------

    def write (self, data):
        """
        Immediately write data.
        """

        raise ChannelException("BlockingChannelClient.write() must be overridden")

# ----------------------------------------------------------------------------------------------------------------------

class HostClient (Client):

    def __init__ (self, host_socket, host_address, server):
        """
        Create a new HostClient instance.

        @param host_socket  (socket) The host socket.
        @param host_address (tuple)  A two-part tuple containing the host ip and port.
        @param server       (Server) The Server instance within which this HostClient is being created.
        """

        Client.__init__(self, host_socket, host_address, server, None)

        self._events        = EVENT_READ
        self._handle_client = server.handle_client
        self._is_host       = True

    # ------------------------------------------------------------------------------------------------------------------

    def handle_read (self):
        """
        Accept a new client connection.
        """

        if not self._server._is_long_running or not self._server._is_serving_client:
            client_socket, client_address = self._client_socket.accept()

            try:
                self._server.register_client(self._handle_client(client_socket, client_address, self._client_address))

            except Exception, e:
                client_socket.close()
