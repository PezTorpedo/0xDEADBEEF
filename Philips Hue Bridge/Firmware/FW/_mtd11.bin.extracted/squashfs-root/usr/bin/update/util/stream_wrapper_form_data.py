# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

import hashlib
from asyncio import StreamReader
from binascii import hexlify

import config
from util.bytebuffer import ByteBuffer
from util.stream_wrapper_base import EndOfStreamError, StreamWrapperBase


class StreamWrapperFormData(StreamWrapperBase):
    def __init__(self, reader: StreamReader, seed: bytes, end_sentinel: bytes):
        self.__digest = hashlib.md5()
        self.__md5 = None
        self.__size = 0
        self.__reader = reader
        self.__seed = seed
        self.__end_sentinel = end_sentinel

    async def __aenter__(self) -> "StreamWrapperFormData":
        return self

    async def __aexit__(self, *_):
        pass

    def md5(self) -> str:
        if self.__md5 is None:
            self.__md5 = hexlify(self.__digest.digest()).decode().strip()
        return self.__md5

    def __update_digest(self, data: memoryview) -> memoryview:
        self.__digest.update(data)
        self.__size += len(data)
        return data

    async def stream(self, consumer, checksum: str = None) -> int:
        end_sentinel_len = len(self.__end_sentinel)
        buffer = ByteBuffer(config.libflasher_chunk_size, self.__seed)
        while True:
            if buffer.size >= end_sentinel_len:
                data_end = buffer.find(self.__end_sentinel)
                if data_end == -1:
                    # In the worst case we are missing 1 byte of the end sentinel.
                    safe_data_len = buffer.size - end_sentinel_len + 1
                    consumer(self.__update_digest(buffer[:safe_data_len]))
                    buffer.discard(safe_data_len)
                else:
                    consumer(self.__update_digest(buffer[:data_end]))
                    break
            if not await buffer.fill_from(self.__reader):
                raise EndOfStreamError()
        return self.__size
