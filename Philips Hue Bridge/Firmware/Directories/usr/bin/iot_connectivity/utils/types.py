import struct
import sys

try:
    import uctypes as ctypes
except ImportError:
    import ctypes

# the following code is useful mostly for the C (ffi) wrappers

_int_size = 8 if sys.maxsize > 2**32 else 4
_unsigned_int_fmt = 'I' if _int_size == 4 else 'Q'


class Size_tByReference(bytearray):
    def __init__(self):
        super().__init__(_int_size)

    def __int__(self) -> int:
        return struct.unpack(_unsigned_int_fmt, self)[0]


class Ptr(bytearray):
    def __init__(self, obj):
        address = struct.pack(_unsigned_int_fmt, ctypes.addressof(obj))
        super().__init__(address)

    def dereference(self, length: int) -> bytearray:
        address = struct.unpack(_unsigned_int_fmt, self)[0]
        ctypes.bytearray_at(address, length)
