# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

import ffi
import uctypes as ctypes


class ByteBuffer:
    __libc = ffi.open("libc.so.6")
    __memmem = __libc.func("p", "memmem", "pIpI")

    def __init__(self, capacity: int, seed=None):
        self.__buffer = bytearray(capacity)
        if seed:
            self.__size = len(seed)
            self.__buffer[: self.__size] = seed
        else:
            self.__size = 0

    @property
    def size(self) -> int:
        return self.__size

    def __getitem__(self, index):
        if isinstance(index, slice):
            return memoryview(self.__buffer)[: self.__size][index]
        raise ValueError("Subscripting is not supported")

    def find(self, needle) -> int:
        """
        Finds the starting offset of the given sequence of bytes in self.
        Will return -1 if not found.
        """
        needle_ptr = self.__memmem(self.__buffer, self.__size, needle, len(needle))
        if needle_ptr:
            return needle_ptr - ctypes.addressof(self.__buffer)
        return -1

    async def fill_from(self, reader) -> bool:
        """
        Reads up to `capacity - size` bytes from the provided reader into
        the free space. The resulting size grows by the actual number
        of bytes read. Will return False if read failed.
        """
        bytes_read = await reader.readinto(memoryview(self.__buffer)[self.__size :])
        self.__size += bytes_read
        return bool(bytes_read)

    def discard(self, count: int):
        """
        Discards `count` bytes from the beginning of the buffer
        and shifts the remainder left. The resulting size will become
        `count` bytes less.
        """
        if count > self.__size:
            raise ValueError(f"Can't shift by {count} bytes, size={self.__size}")
        if count == self.__size:
            self.__size = 0
            return
        tail = self.__size - count
        self.__buffer[:tail] = memoryview(self.__buffer)[count : count + tail]
        self.__size -= count
