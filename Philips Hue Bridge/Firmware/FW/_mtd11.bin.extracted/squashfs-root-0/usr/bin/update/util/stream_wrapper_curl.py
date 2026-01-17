# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

import hashlib
from asyncio import Event, Task
from asyncio import core as asyncio_core
from asyncio import create_task, current_task, sleep_ms
from binascii import hexlify

import config
import uctypes
import util.curl.c_api as curl
from util.diagnostics import loggable
from util.misc import wait_ex_ms
from util.stream_wrapper_base import HttpError, StreamChecksumError, StreamSizeError, StreamWrapperBase

# This file contains libcurl bindings, implemented in
# asyncio-friendly way.
#
# The basic principle of operation is as follows.
#
# The libcurl "multi" interface is set up with three callbacks:
#
# 1. Timer callback, which is called by libcurl when it needs
#    to start or stop a timer,
# 2. Socket callback, which is called by libcurl when it needs
#    to be notified about socket events, such as "ready to read",
#    or "ready to write", and finally
# 3. Data callback, which is called by libcurl when it has some
#    data for us.
#
# When the callback 1 or 2 is invoked, we perform the action libcurl
# has requested, and notify it by calling `curl_multi_socket_action`
# with appropriate parameters, which in turn will perform (a part of)
# the actual network exchange and then invoke one of the three
# callbacks again to continue.


class CurlError(Exception):
    def __init__(self, code: int, errno: int):
        self.__code = code
        self.__errno = errno

    def terminal(self) -> bool:
        # CURLE_SSL_CONNECT_ERROR happens when mbedtls can't allocate memory.
        return self.__code in (curl.CURLE_OUT_OF_MEMORY, curl.CURLE_SSL_CONNECT_ERROR)

    def __str__(self) -> str:
        errno_text = f", errno={self.__errno}" if self.__errno else ""
        return f"code={self.__code}, message={curl.curl_easy_strerror(self.__code)}{errno_text}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(code={self.__code}, errno={self.__errno})"


# It appears that we can't create libffi callbacks from
# bound methods. It pretends to work at first, but ends up
# corrupting stack and behaving very badly.
# To work around that we keep out callbacks as regular functions,
# and pass in the current StreamCurl instance via the user pointer.
__instances = {}


def __receive_callback(userp: int) -> int:
    # Curlaux buffer is full, trigger the receive task and pause the transfer.
    self: StreamWrapperCurl = __instances[userp]
    self.__receive_event.set()
    self.__receive_paused = True
    return curl.CURL_WRITEFUNC_PAUSE


def __socket_callback(easy, s, action, userp, socketp):
    # CURL wants us to start or stop monitoring a socket for events.
    self: StreamWrapperCurl = __instances[userp]
    self.__debug("socket_callback(0x%x, %d, 0x%0x, 0x%0x, 0x%0x)", easy, s, action, userp, socketp)
    if action & curl.CURL_POLL_IN:
        # CURL wants to be notified when it can read data from the socket.
        if self.__read_monitor_task is None or self.__read_monitor_task.done():
            self.__debug("socket_callback, starting read monitor task")
            self.__read_monitor_task = create_task(self.__read_monitor_worker(s))
    elif self.__read_monitor_task is not None and not self.__read_monitor_task.done():
        # CURL is no longer interested in reading.
        self.__debug("socket_callback, stopping read monitor task")
        if self.__read_monitor_task != current_task():
            self.__read_monitor_task.cancel()
        self.__read_monitor_task = None
    if action & curl.CURL_POLL_OUT:
        # CURL wants to be notified when it can write data to the socket.
        if self.__write_monitor_task is None or self.__write_monitor_task.done():
            self.__debug("socket_callback, starting write monitor task")
            self.__write_monitor_task = create_task(self.__write_monitor_worker(s))
    elif self.__write_monitor_task is not None and not self.__write_monitor_task.done():
        # CURL is no longer interested in writing.
        self.__debug("socket_callback, stopping write monitor task")
        if self.__write_monitor_task != current_task():
            self.__write_monitor_task.cancel()
        self.__write_monitor_task = None
    return 0


def __timer_callback(multi, timeout, userp):
    # CURL wants us to start or stop a timer.
    self: StreamWrapperCurl = __instances[userp]
    self.__debug("timer_callback(0x%x, %d, 0x%0x)", multi, timeout, userp)
    self.__timer_request = timeout
    self.__timer_event.set()
    return 0


# We need to keep references to ffi callbacks, to prevent
# those from being garbage collected.
__socket_callback_w = curl.wrap_socket_callback(__socket_callback)
__timer_callback_w = curl.wrap_timer_callback(__timer_callback)
__receive_callback_w = curl.wrap_data_callback(__receive_callback)


@loggable
class StreamWrapperCurl(StreamWrapperBase):
    def __init__(self, url: str, size_budget: int):
        self.__digest = hashlib.md5()
        self.__md5 = None
        self.__url = url
        self.__size_budget = size_budget

    def __debug(self, format: str, *args):
        if config.libcurl_debug:
            self._logger.debug(f"[{id(current_task()):012x}] {format}", *args)

    async def __aenter__(self) -> 'StreamWrapperCurl':
        __instances[id(self)] = self

        self.__multi_handle = curl.curl_multi_init()
        curl.curl_multi_setopt(self.__multi_handle, curl.CURLMOPT_SOCKETFUNCTION, __socket_callback_w)
        curl.curl_multi_setopt(self.__multi_handle, curl.CURLMOPT_SOCKETDATA, id(self))
        curl.curl_multi_setopt(self.__multi_handle, curl.CURLMOPT_TIMERFUNCTION, __timer_callback_w)
        curl.curl_multi_setopt(self.__multi_handle, curl.CURLMOPT_TIMERDATA, id(self))

        self.__easy_handle = curl.curl_easy_init()
        curl.curl_easy_setopt(self.__easy_handle, curl.CURLOPT_URL, self.__url)
        curl.curl_easy_setopt(self.__easy_handle, curl.CURLOPT_BUFFERSIZE, config.libflasher_chunk_size)
        curl.curl_easy_setopt(self.__easy_handle, curl.CURLOPT_TCP_NODELAY, False)
        curl.curl_easy_setopt(self.__easy_handle, curl.CURLOPT_CAINFO, config.ssl_ca_bundle_path)
        curl.curl_easy_setopt(self.__easy_handle, curl.CURLOPT_SSL_VERIFYPEER, config.ssl_verify_peer)
        curl.curl_easy_setopt(self.__easy_handle, curl.CURLOPT_SSL_VERIFYHOST, config.ssl_verify_host)
        curl.curl_easy_setopt(self.__easy_handle, curl.CURLOPT_FOLLOWLOCATION, True)
        curl.curl_easy_setopt(self.__easy_handle, curl.CURLOPT_MAXREDIRS, 3)
        # There are no "timeouts" in libcurl, but we can simulate one by
        # setting the speed cap such that if less than one chunk is received
        # during the timeout period, the transfer will get aborted.
        curl.curl_easy_setopt(self.__easy_handle, curl.CURLOPT_LOW_SPEED_TIME, config.socket_read_timeout)
        curl.curl_easy_setopt(self.__easy_handle, curl.CURLOPT_LOW_SPEED_LIMIT, config.libflasher_chunk_size)
        curl.curl_easy_setopt(self.__easy_handle, curl.CURLOPT_VERBOSE, config.libcurl_debug)

        # Curlaux will receive the CURL writedata callbacks and buffer
        # the data internally as much as fits. Only when the buffer is full
        # will it call `__receive_callback`. Albeit seemingly occult,
        # this speeds up HTTPS transfers considerably on MIPS platform.
        # This is due to the fact that CURL will feed us data in approximately
        # 1300 byte chunks, so by buffering 16K we reduce the callback rate by
        # a factor of 10, which has a dramatic effect.
        self.__curlaux_handle = curl.curlaux_attach(
            config.libflasher_chunk_size, self.__easy_handle, id(self), __receive_callback_w
        )

        self.__receive_event = Event()
        self.__timer_event = Event()
        self.__receive_paused = False
        self.__timer_request = -1
        self.__timer_task: Task = create_task(self.__timer_task_worker())
        self.__read_monitor_task: Task = None
        self.__write_monitor_task: Task = None

        self._logger.info("ready, url=%s", self.__url)

        # This will invoke the timer and socket callbacks and set the things in motion.
        curl.curl_multi_add_handle(self.__multi_handle, self.__easy_handle)

        return self

    async def __aexit__(self, *_):
        self.__debug("__aexit__, shutting down")
        curl.curl_multi_remove_handle(self.__multi_handle, self.__easy_handle)
        curl.curlaux_detach(self.__curlaux_handle)
        curl.curl_easy_cleanup(self.__easy_handle)
        curl.curl_multi_cleanup(self.__multi_handle)

        # There is a possibility for a race where the timer task
        # will fire after we have cleaned up the CURL handles.
        # We need to make sure that the timer task does not access
        # any CURL functions then.
        timer_task, self.__timer_task = self.__timer_task, None

        # As per usual, a task using `wait_ex` needs a double-tap cancel.
        timer_task.cancel()
        await sleep_ms(10)
        timer_task.cancel()

        del __instances[id(self)]

    async def __timer_task_worker(self):
        while True:
            timeout = True
            if self.__timer_request < 0:
                # There is no timer request, wait for the event forever (or until canceled).
                self.__debug("timer_task_worker sleeping forever")
                await self.__timer_event.wait()
                timeout = False
            elif self.__timer_request > 0:
                # There is a timer request, so sleep the required duration, but allow
                # to be interrupted by the event.
                self.__debug("timer_task_worker sleeping, timeout=%d", self.__timer_request)
                timeout = await wait_ex_ms(self.__timer_event, self.__timer_request)
            self.__timer_event.clear()
            if self.__timer_task != current_task():
                # See the related comment in `__aexit__`.
                self.__debug("timer_task triggered after clean-up")
                break
            # At this point either the timeout has expired, or the event has been set.
            if timeout:
                self.__timer_request = -1
                # Notify CURL that the timeout it has requested expired.
                self.__debug("timer_task_worker, curl_multi_socket_action(CURL_SOCKET_TIMEOUT)")
                # Be aware that CURL_SOCKET_TIMEOUT is a socketfd and not an event
                running_handles = curl.curl_multi_socket_action(self.__multi_handle, curl.CURL_SOCKET_TIMEOUT, 0)
                self.__debug("timer_task_worker, running_handles=%d", running_handles)
                if not running_handles and not self.__receive_event.is_set():
                    # The transfer ended, so make sure to wake up the receiver task.
                    self.__debug("timer_task_worker, triggering consumer task")
                    self.__receive_event.set()
                # It is possible that `curl_multi_socket_action` has requested another
                # timer (via `timer_callback`). That would mean that `timer_request`
                # has been set to something, and the event has been set.
                # That would cause the outer loop to spin twice before settling.
            else:
                # We were interrupted. This means that `timer_request` has
                # been updated. The event is not set, so the request will
                # get handled on the next iteration of the outer loop.
                self.__debug("timer_task_worker interrupted")

    async def __read_monitor_worker(self, socket):
        # Wait until the provided socket is ready for read and notify CURL,
        # in a loop until canceled.
        async def queue_read():
            yield asyncio_core._io_queue.queue_read(socket)

        while True:
            self.__debug("read_monitor_worker, waiting for socket event")
            await queue_read()
            # Notify CURL that it can read from socket.
            self.__debug("read_monitor_worker, curl_multi_socket_action(CURL_CSELECT_IN)")
            running_handles = curl.curl_multi_socket_action(self.__multi_handle, socket, curl.CURL_CSELECT_IN)
            self.__debug("read_monitor_worker, running_handles=%d", running_handles)
            if not running_handles and not self.__receive_event.is_set():
                # The transfer ended, so make sure to wake up the receiver task.
                self.__debug("read_monitor_worker, triggering consumer task")
                self.__receive_event.set()
            # Make sure CURL is still interested in read events from this socket.
            if self.__read_monitor_task != current_task():
                break

    async def __write_monitor_worker(self, socket):
        # Wait until the provided socket is ready for write and notify CURL,
        # in a loop until canceled.
        async def queue_write():
            yield asyncio_core._io_queue.queue_write(socket)

        while True:
            self.__debug("write_monitor_worker, waiting for socket event")
            # Wait for socket to be ready for writing.
            await queue_write()
            # Notify CURL that it can write to socket.
            self.__debug("write_monitor_worker, curl_multi_socket_action(CURL_CSELECT_OUT)")
            running_handles = curl.curl_multi_socket_action(self.__multi_handle, socket, curl.CURL_CSELECT_OUT)
            self.__debug("write_monitor_worker, running_handles=%d", running_handles)
            if not running_handles and not self.__receive_event.is_set():
                # The transfer ended, so make sure to wake up the receiver task.
                self.__debug("write_monitor_worker, triggering consumer task")
                self.__receive_event.set()
            # Make sure CURL is still interested in write events from this socket.
            if self.__write_monitor_task != current_task():
                break

    def md5(self) -> str:
        if self.__md5 is None:
            self.__md5 = hexlify(self.__digest.digest()).decode().strip()
        return self.__md5

    async def stream(self, consumer, checksum: str = None) -> int:
        # Everything has been set up for us in `__aenter__`, all that is left
        # to do is to wait for receive event and consume data in a loop.
        def read_data() -> bytearray:
            if length := curl.curlaux_get_length(self.__curlaux_handle):
                self.__debug("stream, received %d bytes", length)
                return uctypes.bytearray_at(curl.curlaux_get_data(self.__curlaux_handle), length)
            return None

        def consume_data(data: bytearray):
            if data:
                consumer(data)
                self.__digest.update(data)
                curl.curlaux_clean(self.__curlaux_handle)

        while True:
            self.__debug("stream, consumer task sleeping")
            await self.__receive_event.wait()
            self.__debug("stream, consumer task triggered")
            content_length = curl.curl_easy_getinfo(self.__easy_handle, curl.CURLINFO_CONTENT_LENGTH_DOWNLOAD_T)
            self.__debug("stream, content_length=%d", content_length)
            if self.__size_budget and content_length != -1:
                if content_length > self.__size_budget:
                    raise StreamSizeError(self.__size_budget, content_length)
                self.__size_budget = None
            # We need to check if the transfer is complete the first thing
            # in order to avoid forwarding data to the consumer only to discover
            # immediately after that it was an error response body.
            # We do make an assumption that any error response body
            # will be small enough to fit into the receive buffer.
            # Failing that assumption we will forward the response
            # body to the consumer, where it will be discarded.
            if status := curl.curl_multi_info_read(self.__multi_handle):
                self.__debug("stream, msg=%d, result=%d", status.msg, status.result)
                if status.result == 0:
                    response_code = curl.curl_easy_getinfo(self.__easy_handle, curl.CURLINFO_RESPONSE_CODE)
                    self.__debug("stream, response_code=%d", response_code)
                    if response_code // 100 == 2:
                        # We may still have data in the buffer.
                        consume_data(read_data())
                        if checksum and checksum != self.md5():
                            raise StreamChecksumError(content_length, checksum, self.md5())
                        self._logger.info("Done with download, length=%d, md5=%s", content_length, self.md5())
                        return content_length
                    # The buffer should now contain the non-2xx response body.
                    body = read_data()
                    raise HttpError(response_code, body[:1024] if body else b"")
                errno = curl.curl_easy_getinfo(self.__easy_handle, curl.CURLINFO_OS_ERRNO)
                raise CurlError(status.result, errno)
            # The transfer is still active, forward the data to the consumer.
            consume_data(read_data())
            # We can resume receiving data.
            self.__receive_event.clear()
            if self.__receive_paused:
                self.__debug("stream, resuming transfer")
                self.__receive_paused = False
                curl.curl_easy_pause(self.__easy_handle, curl.CURLPAUSE_CONT)
