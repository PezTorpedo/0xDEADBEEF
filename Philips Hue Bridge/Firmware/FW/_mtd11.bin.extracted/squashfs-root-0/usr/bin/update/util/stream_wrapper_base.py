# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.


class HttpError(Exception):
    def __init__(self, status: int, body: bytes = None):
        self.status = status
        self.body = body

    def __str__(self) -> str:
        return "{}".format(self.status)


class StreamChecksumError(Exception):
    """
    Raised when the checksum check on the downloaded file fails.

    Attributes:
        expected: the expected md5.
        actual:   the actual md5.
        size:     the size of the file over which the md5 was computed.
    """

    def __init__(self, size: int, expected: str, actual: str):
        self.size = size
        self.expected = expected
        self.actual = actual

    def __str__(self) -> str:
        return f"size={self.size}, expected_md5={self.expected}, actual_md5={self.actual}"


class StreamSizeError(Exception):
    """
    Raised when the content length exceeds the configured budget.

    Attributes:
        budget: the maximum allowed size.
        actual: the sctual size.
    """

    def __init__(self, budget: int, actual: int):
        self.__budget = budget
        self.__actual = actual

    def __str__(self) -> str:
        return f"budget={self.__budget}, actual={self.__actual}"


class EndOfStreamError(Exception):
    """Raised when the sideloading connection is dropped."""

    def __str__(self):
        return "connection reset by peer"


class StreamWrapperBase:
    async def stream(self, consumer, checksum: str = None) -> int:
        raise NotImplementedError()
