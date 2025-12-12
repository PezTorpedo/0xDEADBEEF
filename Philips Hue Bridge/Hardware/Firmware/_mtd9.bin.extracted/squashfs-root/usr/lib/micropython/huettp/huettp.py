# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

from asyncio import StreamReader, open_connection, wait_for


class ClientResponse:
    """Returned from `huettp.request()` call and allows reading the server response.

    Attributes:
            status: the HTTP status code.
            headers: dictionary of HTTP response headers where key is
                     the lowercase header name and value is the list of header
                     values with leading whitespace removed. List is used to
                     support headers with multiple values (e.g. comma-separated
                     or just multiple instances of the same header)
    """

    status: int
    headers: dict

    async def read(self, size: int) -> bytes:
        """Read and return up to `size` bytes.

        This is a coroutine.

        Raises:
            OSError:      when the socket operation fails.
            TimeoutError: when the socket operation times out.
        """
        raise NotImplementedError()

    async def readinto(self, buffer: bytes) -> int:
        """Read into a pre-allocated buffer and return the actual number of bytes read.

        This is a coroutine.

        Raises:
            OSError:      when the socket operation fails.
            TimeoutError: when the socket operation times out.
        """
        raise NotImplementedError()


class __PlainResponse(ClientResponse):
    def __init__(self, reader: StreamReader, content_length: int):
        self.content = reader
        self.remaining_length = content_length

    async def read(self, size=-1) -> bytes:
        if self.remaining_length > 0:
            data = await self.content.read(size)
            self.remaining_length -= len(data)
            return data
        return b""

    async def readinto(self, buffer: bytes) -> int:
        if self.remaining_length > 0:
            bytes_read = await self.content.readinto(buffer)
            self.remaining_length -= bytes_read
            return bytes_read
        return 0

    def __repr__(self) -> str:
        return "<__PlainResponse %d %s>" % (self.status, self.headers)  # pylint: disable=consider-using-f-string


class __ChunkedResponse(ClientResponse):
    def __init__(self, reader: StreamReader):
        self.content = reader
        self.chunk_size = 0

    async def read(self, size=4 * 1024 * 1024) -> bytes:
        if self.chunk_size == 0:
            line = await self.content.readline()
            line = line.split(b";", 1)[0]
            self.chunk_size = int(line, 16)
            if self.chunk_size == 0:
                # End of message
                separator = await self.content.read(2)
                assert separator == b"\r\n"
                return b""
        data = await self.content.read(min(size, self.chunk_size))
        self.chunk_size -= len(data)
        if self.chunk_size == 0:
            separator = await self.content.read(2)
            assert separator == b"\r\n"
        return data

    async def readinto(self, buffer: bytes) -> int:
        if self.chunk_size == 0:
            line = await self.content.readline()
            line = line.split(b";", 1)[0]
            self.chunk_size = int(line, 16)
            if self.chunk_size == 0:
                # End of message
                separator = await self.content.read(2)
                assert separator == b"\r\n"
                return b""
        bytes_read = await self.content.readinto(buffer)
        self.chunk_size -= bytes_read
        if self.chunk_size == 0:
            separator = await self.content.read(2)
            assert separator == b"\r\n"
        return bytes_read

    def __repr__(self) -> str:
        return "<__ChunkedResponse %d %s>" % (self.status, self.headers)  # pylint: disable=consider-using-f-string


def __split_url(url: str):
    try:
        protocol, _, host, path = url.split("/", 3)
    except ValueError:
        protocol, _, host = url.split("/", 2)
        path = ""

    if protocol == "http:":
        port = 80
    elif protocol == "https:":
        port = 443
    else:
        raise ValueError("Unsupported protocol: " + protocol)

    # Cut off credentials if present before trying to parse port number.
    host_port = host.rsplit("@", 1)[-1]
    try:
        host, port = host_port.rsplit(":", 1)
    except ValueError:
        pass

    return (protocol, host, port, path)


async def __request_raw(method: str, url: str, proxy: str, headers: dict, timeout: float) -> StreamReader:
    protocol, host, port, path = __split_url(url)
    _, proxy_host, proxy_port, _ = __split_url(proxy) if proxy else (None, host, port, None)

    if not proxy and protocol == "https:":
        # We can't use HTTPS without forward proxy because of uPython issues
        # so we don't allow HTTPS requests without proxy.
        raise ValueError("Attempted HTTPS connection without proxy")

    if timeout is not None:
        reader, writer = await wait_for(open_connection(proxy_host, proxy_port), timeout)
    else:
        reader, writer = await open_connection(proxy_host, proxy_port)

    # Use protocol 1.0, because 1.1 always allows to use chunked transfer-encoding
    # But explicitly set Connection: close, even though this should be default for 1.0,
    # because some servers misbehave w/o it.
    query = f"{method} /{path} HTTP/1.0\r\n"
    query += f"Host: {host}\r\n"
    query += "Connection: close\r\n"
    query += "User-Agent: compat\r\n"
    if proxy:
        query += f"x-forwarded-to: {protocol}//{host}:{port}\r\n"
    for k, v in headers.items():
        query += f"{k}: {v}\r\n"
    query += "\r\n"

    await writer.awrite(query.encode("latin-1"))

    return reader


def __decode_http_header(line: bytes) -> tuple:
    """Splits the HTTP header to its key and value.

    Parameters:
    line (bytes): Header line, for example "'Content-Length': 12333"

    Returns:
    str, str: tuple where first element is a header key in lowercase and the
              second is string representation of value with leading whitespace
              removed. For example above the function will return
              'content-length', '12333'.
    """
    header = line.decode().split(":", 1)
    if len(header) <= 1:
        return None, None
    return header[0].lower(), header[1].lstrip()


async def request(
    method: str, url: str, proxy: str = None, headers: dict = None, timeout: float = None
) -> ClientResponse:
    """Makes a `method` HTTP request to `url` and returns a `ClientResponse`
    instance, allowing reading the response.
    """
    redirect_count = 0
    content_length = 0
    while redirect_count < 2:
        reader = await __request_raw(method, url, proxy, headers if headers else {}, timeout)
        response_headers = {}
        status_line = await reader.readline()
        status_line = status_line.split(None, 2)
        status = int(status_line[1])
        chunked = False
        while True:
            header_line = await reader.readline()
            if not header_line or header_line == b"\r\n":
                break
            header_name, header_value = __decode_http_header(header_line)
            # RFC 7230 generally does not allow for multiple HTTP headers but
            # there's an exception for Set-Cookie header. As it turned out
            # some clouds also send some other headers with multiple values.
            # As there's no native multidict in the uPython, we're using a
            # list of HTTP header values in that case.
            if header_name not in response_headers:
                response_headers[header_name] = []
            response_headers[header_name].append(header_value)

            if header_name == "transfer-encoding" and header_value.lower() == "chunked":
                chunked = True
            elif header_name == "location":
                url = header_value.strip()
            elif header_name == "content-length":
                content_length = int(header_value)

        if 301 <= status <= 303:
            redirect_count += 1
            await reader.aclose()
            continue
        break

    if chunked:
        response = __ChunkedResponse(reader)
    else:
        response = __PlainResponse(reader, content_length)

    response.status = status
    response.headers = response_headers

    return response
