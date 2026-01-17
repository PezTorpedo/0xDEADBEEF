# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

import asyncio
import errno
import gc
import re
from asyncio import StreamReader, StreamWriter
from asyncio.stream import Server
from collections import namedtuple
from logging import Logger

from util.diagnostics import loggable
from util.persistence import DataObject

_Endpoint = namedtuple("_Endpoint", "method uri callback headers")
_Status = namedtuple("_Status", "code message")


class Response(DataObject):
    OK = _Status(200, "OK")
    BAD_REQUEST = _Status(400, "Bad Request")
    FORBIDDEN = _Status(403, "Forbidden")
    NOT_FOUND = _Status(404, "Not Found")
    I_AM_A_TEAPOT = _Status(418, "I'm a teapot")
    INTERNAL_SERVER_ERROR = _Status(500, "Internal Server Error")

    def __init__(self, **kwargs):
        assert "status" in kwargs
        assert "content_type" in kwargs
        assert "body" in kwargs
        super().__init__(**kwargs)
        if "headers" not in self:
            self.update(headers=None)


@loggable
class HttpServer:
    _logger: Logger
    server: Server = None

    def __init__(self, bind_address: str, port: int):
        self.__endpoints = []
        self.__bind_address = bind_address
        self.__port = port

    async def start(self):
        self.server = await asyncio.start_server(self.__handle_connection, self.__bind_address, self.__port)

    async def stop(self):
        self.server.close()
        await self.server.wait_closed()

    def __send_response_status(self, status, message):
        self._writer.write(f"HTTP/1.0 {status} {message}\r\n")

    def __send_response_headers(self, *headers: dict):
        for h in headers:
            if h:
                for k, v in h.items():
                    self._writer.write(f"{k}: {v}\r\n")
        self._writer.write("\r\n")

    def __send_response(self, status: int, message: str, headers: dict, content_type: str, body: str):
        """
        Sends out a response.

        Parameters:
            status: the HTTP response code
            message: the textual representation of the response code
            headers: the HTTP headers to include in the response
            content_type: the HTTP content-type
            body: the response body
        """
        try:
            self.__send_response_status(status, message)
            self.__send_response_headers(headers, {"Content-Type": content_type, "Content-Length": len(body)})
            self._writer.write(body)
        except OSError as e:
            if e.errno != errno.EPIPE:
                self._logger.warning("Connection closed by peer")
            else:
                self._logger.warning(e)

    async def __handle_connection(self, reader: StreamReader, writer: StreamWriter):
        # Test that peername exists (but don"t check its value, it changes)
        writer.get_extra_info("peername")

        self.reader = reader
        self._writer = writer

        request = await reader.readline()
        method, uri, version = request.decode().strip().split()
        method = method.upper()
        accepted_headers = ["content-length"] + [header for _, _, _, headers in self.__endpoints for header in headers]
        self._logger.info("Incoming request, method=%s, uri=%s, version=%s", method, uri, version)
        self._logger.debug("Accepted headers: %s", accepted_headers)

        headers = {}
        while line := (await reader.readline()).decode().strip():
            header, value = map(lambda s: s.strip(), line.split(":", 1))
            if header.lower() in accepted_headers:
                self._logger.debug("[+] %s: %s", header, value)
                headers[header.lower()] = value
            else:
                self._logger.debug("[-] %s: %s", header, value)

        for endpoint in self.__endpoints:
            if endpoint.method == method and (match := endpoint.uri.match(uri)):
                try:
                    response = await endpoint.callback(self, headers, *match.groups())
                except Exception as ex:
                    self._logger.exception(
                        "%s handler for %s failed with %s(%s)",
                        method,
                        uri,
                        type(ex).__name__,
                        str(ex),
                    )
                    self.__send_response(
                        Response.INTERNAL_SERVER_ERROR.code,
                        Response.INTERNAL_SERVER_ERROR.message,
                        None,
                        "text/html",
                        Response.INTERNAL_SERVER_ERROR.message,
                    )
                    break

                self.__send_response(
                    response.status.code,
                    response.status.message,
                    response.headers,
                    response.content_type,
                    response.body,
                )
                break
        else:
            self._logger.warning("No handler found, method=%s, uri=%s", method, uri)
            self.__send_response(
                Response.NOT_FOUND.code,
                Response.NOT_FOUND.message,
                None,
                "text/html",
                Response.NOT_FOUND.message,
            )
        await writer.drain()
        await self.__drain_reader(reader)
        writer.close()
        await writer.wait_closed()

    async def __drain_reader(self, reader: StreamReader):
        # It may so happen that we decide to send the response before reading
        # the entire request body. For example when we detect some sort of error
        # early in the sideloading process. However, we can't just close the connection,
        # as it will make NGINX very upset and cause it to return 502 Bad Gateway
        # to the sideloading client, instead of our artisan, hand-crafted, and assembled
        # exclusively from ethically sourced bytes error message.
        # So make sure to drain the body and wait for the client to close the connection.
        try:
            while await reader.read(1024):
                gc.collect()
        except OSError as e:
            if e.errno == errno.ECONNRESET:
                self._logger.warning("Connection closed by peer")
            else:
                self._logger.warning(e)

    def register_endpoint(self, method: str, uri: str, callback, headers=()):
        self.__endpoints.append(_Endpoint(method=method, uri=re.compile(uri), callback=callback, headers=headers))
