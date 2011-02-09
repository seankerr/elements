# This file is part of Elements.
# Copyright (c) 2010 Sean Kerr. All rights reserved.
#
# The full license is available in the LICENSE file that was distributed with this source code.
#
# Author: Sean Kerr <sean@code-box.org>

import select

from elements.core.exception import EventException

# ----------------------------------------------------------------------------------------------------------------------

class EventManager:

    def __init__ (self, server):
        """
        Create a new EventManager instance.

        @param server (Server) The Server instance under which this EventManager is being created.
        """

        self._server = server

    # ------------------------------------------------------------------------------------------------------------------

    def modify (self, fileno, events):
        """
        Modify the event list for a file descriptor.

        @param fileno (int) The file descriptor.
        @param events (int) The events.
        """

        raise EventException("EventManager.modify() must be overridden")

    # ------------------------------------------------------------------------------------------------------------------

    def poll (self):
        """
        Poll the event manager for more events.
        """

        raise EventException("EventManager.poll() must be overridden")

    # ------------------------------------------------------------------------------------------------------------------

    def register (self, fileno, events):
        """
        Register events for a file descriptor.

        @param fileno (int) The file descriptor.
        @param events (int) The events.
        """

        raise EventException("EventManager.register() must be overridden")

    # ------------------------------------------------------------------------------------------------------------------

    def unregister (self):
        """
        Unregister a file descriptor.

        @param fileno (int) The file descriptor.
        """

        raise EventException("EventManager.unregister() must be overridden")

# ----------------------------------------------------------------------------------------------------------------------

class KQueueEventManager (EventManager):

    def __init__ (self, server):
        """
        Create a new KQueueEventManager instance.

        @param server (Server) The Server instance under which this KQueueEventManager is being created.
        """

        EventManager.__init__(self, server)

        self._count  = 0
        self._kqueue = select.kqueue()

        self.EVENT_ERROR  = 1
        self.EVENT_READ   = 2
        self.EVENT_WRITE  = 4
        self.EVENT_LINGER = 8

    # ------------------------------------------------------------------------------------------------------------------

    def modify (self, fileno, events):
        """
        Modify the event list for a file descriptor.

        @param fileno (int) The file descriptor.
        @param events (int) The events.
        """

        if events & self.EVENT_READ:
            self._kqueue.control([select.kevent(fileno, select.KQ_FILTER_READ, select.KQ_EV_ADD)], 0)

        if events & self.EVENT_WRITE:
            self._kqueue.control([select.kevent(fileno, select.KQ_FILTER_WRITE, select.KQ_EV_ADD)], 0)

    # ------------------------------------------------------------------------------------------------------------------

    def poll (self):
        """
        Poll the event manager for more events.
        """

        events = {}

        for event in self._kqueue.control(None, self._count, 0.5):
            events[event.ident] = 0

            if event.flags & select.KQ_EV_ERROR:
                events[event.ident] |= self.EVENT_ERROR

            if event.filter == select.KQ_FILTER_READ:
                events[event.ident] |= self.EVENT_READ

            if event.filter == select.KQ_FILTER_WRITE:
                events[event.ident] |= self.EVENT_WRITE

        return events.items()

    # ------------------------------------------------------------------------------------------------------------------

    def register (self, fileno, events):
        """
        Register events for a file descriptor.

        @param fileno (int) The file descriptor.
        @param events (int) The events.
        """

        if events & self.EVENT_READ:
            self._kqueue.control([select.kevent(fileno, select.KQ_FILTER_READ, select.KQ_EV_ADD)], 0)

        if events & self.EVENT_WRITE:
            self._kqueue.control([select.kevent(fileno, select.KQ_FILTER_WRITE, select.KQ_EV_ADD)], 0)

        self._count += 1

    # ------------------------------------------------------------------------------------------------------------------

    def unregister (self, fileno):
        """
        Unregister a file descriptor.

        @param fileno (int) The file descriptor.
        """

        self._kqueue.control([select.kevent(fileno, select.KQ_FILTER_READ, select.KQ_EV_DELETE)], 0)

        self._count -= 1

# ----------------------------------------------------------------------------------------------------------------------

class PollEventManager (EventManager):

    def __init__ (self, server):
        """
        Create a new PollEventManager instance.

        @param server (Server) The Server instance under which this PollEventManager is being created.
        """

        EventManager.__init__(self, server)

        self._poll = select.poll()

        self.EVENT_ERROR  = select.POLLERR | select.POLLNVAL
        self.EVENT_READ   = select.POLLIN | select.POLLPRI
        self.EVENT_WRITE  = select.POLLOUT
        self.EVENT_LINGER = select.POLLHUP

    # ------------------------------------------------------------------------------------------------------------------

    def modify (self, fileno, events):
        """
        Modify the event list for a file descriptor.

        @param fileno (int) The file descriptor.
        @param events (int) The events.
        """

        self._poll.modify(fileno, events)

    # ------------------------------------------------------------------------------------------------------------------

    def poll (self):
        """
        Poll the event manager for more events.
        """

        return self._poll.poll(0.5)

    # ------------------------------------------------------------------------------------------------------------------

    def register (self, fileno, events):
        """
        Register events for a file descriptor.

        @param fileno (int) The file descriptor.
        @param events (int) The events.
        """

        self._poll.register(fileno, events)

    # ------------------------------------------------------------------------------------------------------------------

    def unregister (self, fileno):
        """
        Unregister a file descriptor.

        @param fileno (int) The file descriptor.
        """

        self._poll.unregister(fileno)

# ----------------------------------------------------------------------------------------------------------------------

class EPollEventManager (PollEventManager):

    def __init__ (self, server):
        """
        Create a new EPollEventManager instance.

        @param server (Server) The Server instance under which this EPollEventManager is being created.
        """

        PollEventManager.__init__(self, server)

        self._poll = select.epoll()

        self.EVENT_ERROR  = select.EPOLLERR
        self.EVENT_READ   = select.EPOLLIN | select.EPOLLPRI
        self.EVENT_WRITE  = select.EPOLLOUT
        self.EVENT_LINGER = select.EPOLLHUP

# ----------------------------------------------------------------------------------------------------------------------

class SelectEventManager (EventManager):

    def __init__ (self, server):
        """
        Create a new SelectEventManager instance.

        @param server (Server) The Server instance under which this SelectEventManager is being created.
        """

        EventManager.__init__(self, server)

        self._error_filenos = set()
        self._read_filenos  = set()
        self._write_filenos = set()

        self.EVENT_ERROR  = 1
        self.EVENT_READ   = 2
        self.EVENT_WRITE  = 4
        self.EVENT_LINGER = 8

    # ------------------------------------------------------------------------------------------------------------------

    def modify (self, fileno, events):
        """
        Modify the event list for a file descriptor.

        @param fileno (int) The file descriptor.
        @param events (int) The events.
        """

        if events & self.EVENT_ERROR:
            self._error_filenos.add(fileno)

        else:
            self._error_filenos.discard(fileno)

        if events & self.EVENT_READ:
            self._read_filenos.add(fileno)

        else:
            self._read_filenos.discard(fileno)

        if events & self.EVENT_WRITE:
            self._write_filenos.add(fileno)

        else:
            self._write_filenos.discard(fileno)

    # ------------------------------------------------------------------------------------------------------------------

    def poll (self):
        """
        Poll the event manager for more events.
        """

        events = {}

        read_filenos, write_filenos, error_filenos = select.select(self._read_filenos, self._write_filenos,
                                                                   self._error_filenos, 0.5)

        for fileno in read_filenos:
            events[fileno] = self.EVENT_READ

        for fileno in write_filenos:
            events[fileno] = events.get(fileno, 0) | self.EVENT_WRITE

        for fileno in error_filenos:
            events[fileno] = events.get(fileno, 0) | self.EVENT_ERROR

        return events.items()

    # ------------------------------------------------------------------------------------------------------------------

    def register (self, fileno, events):
        """
        Register events for a file descriptor.

        @param fileno (int) The file descriptor.
        @param events (int) The events.
        """

        if events & self.EVENT_ERROR:
            self._error_filenos.add(fileno)

        if events & self.EVENT_READ:
            self._read_filenos.add(fileno)

        if events & self.EVENT_WRITE:
            self._write_filenos.add(fileno)

    # ------------------------------------------------------------------------------------------------------------------

    def unregister (self, fileno):
        """
        Unregister a file descriptor.

        @param fileno (int) The file descriptor.
        """

        self._error_filenos.discard(fileno)
        self._read_filenos.discard(fileno)
        self._write_filenos.discard(fileno)
