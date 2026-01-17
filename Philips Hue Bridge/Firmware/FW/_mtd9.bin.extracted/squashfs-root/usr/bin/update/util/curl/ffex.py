# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

import struct
import sys

import ffi

__A_HANDFUL_OF_NOTHING = object()


def __memoize(func):
    memoized_values = {}

    def wrapper(*args):
        if args not in memoized_values:
            memoized_values[args] = func(*args)
        return memoized_values[args]

    return wrapper


@__memoize
def __dlopen(library: str):
    return ffi.open(library)


NULL = 0
LONG = "i"
LONG_LONG = "q"


class NativeError(Exception):
    def __init__(self, function_name: str, return_value, decoder=None, terminal=False):
        decoded = f" - {decoder(return_value)}" if decoder else ""
        super().__init__(f"{function_name} returned unexpected value ({return_value}{decoded})")
        self.__terminal = terminal

    def terminal(self) -> bool:
        return self.__terminal


class Reference(bytearray):
    def __init__(self, native_type):
        super().__init__(struct.calcsize(native_type))
        self.__native_type = native_type

    @property
    def value(self):
        return struct.unpack(self.__native_type, self)[0]

    @value.setter
    def value(self, val):
        struct.pack_into(self.__native_type, self, 0, val)


def native(
    dlib: str,
    returns: str = "v",
    arguments: str = "",
    name: str = None,
    must_return=__A_HANDFUL_OF_NOTHING,
    must_not_return=__A_HANDFUL_OF_NOTHING,
    decoder=None,
    die_on_error=False,
):
    def decorator(decorated_func):
        native_func = __dlopen(dlib).func(returns, name if name else decorated_func.__name__, arguments)
        if must_return is not __A_HANDFUL_OF_NOTHING:

            def must_return_wrapper(*args):
                ret = native_func(*args)
                if ret != must_return:
                    raise NativeError(decorated_func.__name__, ret, decoder, die_on_error)

            return must_return_wrapper
        if must_not_return is not __A_HANDFUL_OF_NOTHING:

            def must_not_return_wrapper(*args):
                ret = native_func(*args)
                if ret == must_not_return:
                    raise NativeError(decorated_func.__name__, ret, decoder, die_on_error)
                return ret

            return must_not_return_wrapper
        return native_func

    return decorator


def native_argument_out(of_type: str):
    def decorator(decorated_func):
        def wrapper(*args):
            out = Reference(of_type)
            # Invoke the decorated function with one extra argument,
            # which is a pointer to a byte buffer of sufficient size
            # to hold a native type specified by `of_type` struct
            # format character.
            decorated_func(*(args + (out,)))
            # Return the decoded value of the `out` argument
            # instead of the decorated function return value.
            return out.value

        return wrapper

    return decorator


def native_64_bit() -> bool:
    return sys.maxsize > (2**31 - 1)
