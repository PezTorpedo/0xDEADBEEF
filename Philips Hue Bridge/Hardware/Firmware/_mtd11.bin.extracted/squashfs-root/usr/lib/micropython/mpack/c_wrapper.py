# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

import ffi

try:
    _libc = ffi.open("libc.so.6")  # Ubuntu and OpenWRT (musl)
except BaseException:
    _libc = ffi.open("libc.so.1")  # QSDK (uclibc)

_mpack = ffi.open("libmpack.so")
_mpack_aux = ffi.open("libmpackaux.so")

free = _libc.func("v", "free", "p")


class MpackType:
    missing = 0
    nil = 1
    bool = 2
    int = 3
    uint = 4
    float = 5
    double = 6
    str = 7
    bin = 8
    array = 9
    map = 10
    ext = 11


new_writer = _mpack_aux.func("p", "new_writer", "")

new_reader = _mpack_aux.func("p", "new_reader", "")

new_tag = _mpack_aux.func("p", "new_tag", "")

mpack_read_tag_p = _mpack_aux.func("v", "mpack_read_tag_p", "pp")

mpack_writer_init_growable = _mpack.func("v", "mpack_writer_init_growable", "ppp")

mpack_write_nil = _mpack.func("v", "mpack_write_nil", "p")

_mpack_write_bool = _mpack.func("v", "mpack_write_bool", "pi")


def mpack_write_bool(writer, value):
    return _mpack_write_bool(writer, int(value))


mpack_write_int = _mpack.func("v", "mpack_write_int", "pq")

mpack_write_double = _mpack.func("v", "mpack_write_double", "pd")

mpack_write_utf8_cstr = _mpack.func("v", "mpack_write_utf8_cstr", "pp")

mpack_write_bin = _mpack.func("v", "mpack_write_bin", "ppi")

mpack_start_array = _mpack.func("v", "mpack_start_array", "pi")

mpack_finish_array = _mpack.func("v", "mpack_finish_array", "p")

mpack_start_map = _mpack.func("v", "mpack_start_map", "pi")

mpack_finish_map = _mpack.func("v", "mpack_finish_map", "p")

mpack_writer_destroy = _mpack.func("i", "mpack_writer_destroy", "p")

mpack_reader_init_data = _mpack.func("v", "mpack_reader_init_data", "ppi")

mpack_tag_type = _mpack.func("i", "mpack_tag_type", "p")

_mpack_tag_bool_value = _mpack.func("i", "mpack_tag_bool_value", "p")


def mpack_tag_bool_value(tag):
    return bool(_mpack_tag_bool_value(tag))


mpack_tag_int_value = _mpack.func("q", "mpack_tag_int_value", "p")

mpack_tag_uint_value = _mpack.func("Q", "mpack_tag_uint_value", "p")

mpack_tag_float_value = _mpack.func("f", "mpack_tag_float_value", "p")

mpack_tag_double_value = _mpack.func("d", "mpack_tag_double_value", "p")

mpack_tag_bytes = _mpack.func("i", "mpack_tag_bytes", "p")

mpack_read_utf8_inplace = _mpack.func("p", "mpack_read_utf8_inplace", "pi")

mpack_read_bytes_inplace = _mpack.func("p", "mpack_read_bytes_inplace", "pi")

mpack_tag_array_count = _mpack.func("i", "mpack_tag_array_count", "p")

mpack_done_array = _mpack.func("v", "mpack_done_array", "p")

mpack_tag_map_count = _mpack.func("i", "mpack_tag_map_count", "p")

mpack_done_map = _mpack.func("v", "mpack_done_map", "p")

mpack_reader_destroy = _mpack.func("i", "mpack_reader_destroy", "p")

mpack_reader_error = _mpack.func("i", "mpack_reader_error", "p")
