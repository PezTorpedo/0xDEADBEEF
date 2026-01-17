# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

from asyncio import StreamReader

from util.stream_wrapper_base import (  # noqa
    EndOfStreamError,
    HttpError,
    StreamChecksumError,
    StreamSizeError,
    StreamWrapperBase,
)
from util.stream_wrapper_curl import CurlError, StreamWrapperCurl  # noqa
from util.stream_wrapper_form_data import StreamWrapperFormData


async def stream_wrapper_from_reader(reader: StreamReader, seed: bytes, end_sentinel: bytes) -> "StreamWrapperBase":
    return StreamWrapperFormData(reader, seed, end_sentinel)


async def stream_wrapper_from_url(url: str, size_budget: int = None) -> "StreamWrapperBase":
    return StreamWrapperCurl(url, size_budget)


class StreamSpy:
    def __init__(self, size: int, consumer):
        self.__size = size
        self.__consumer = consumer
        self.data = b""

    def __call__(self, data: memoryview) -> int:
        if self.__size:
            self.data += bytes(data[: self.__size])
            self.__size = 0 if len(data) >= self.__size else self.__size - len(data)
        return self.__consumer(data)
