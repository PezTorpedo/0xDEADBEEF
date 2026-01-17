# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

import uctypes as ctypes

from hueutils.ctypes_adapter import ByReference, Ptr

from .c_wrapper import (
    MpackType,
    free,
    mpack_done_array,
    mpack_done_map,
    mpack_finish_array,
    mpack_read_bytes_inplace,
    mpack_read_tag_p,
    mpack_read_utf8_inplace,
    mpack_reader_destroy,
    mpack_reader_init_data,
    mpack_start_array,
    mpack_start_map,
    mpack_tag_array_count,
    mpack_tag_bool_value,
    mpack_tag_bytes,
    mpack_tag_double_value,
    mpack_tag_float_value,
    mpack_tag_int_value,
    mpack_tag_map_count,
    mpack_tag_type,
    mpack_tag_uint_value,
    mpack_write_bin,
    mpack_write_bool,
    mpack_write_double,
    mpack_write_int,
    mpack_write_nil,
    mpack_write_utf8_cstr,
    mpack_writer_destroy,
    mpack_writer_init_growable,
    new_reader,
    new_tag,
    new_writer,
)


def dumps(obj):
    writer = new_writer()
    buffer_size = ByReference()
    output = Ptr(bytearray(0))
    mpack_writer_init_growable(writer, output, buffer_size)

    _dump(obj, writer)

    err = mpack_writer_destroy(writer)
    free(writer)

    if err:
        raise RuntimeError

    res = output.dereference(int(buffer_size))

    return res


def loads(msg):
    reader = new_reader()
    mpack_reader_init_data(reader, msg, len(msg))
    tag = new_tag()

    res = _load(reader, tag)

    err = mpack_reader_destroy(reader)

    free(reader)
    free(tag)

    if err:
        raise RuntimeError

    return res


def _dump(obj, writer):
    t = type(obj)

    if t is list:
        mpack_start_array(writer, len(obj))
        for el in obj:
            _dump(el, writer)
        mpack_finish_array(writer)
    elif t is dict:
        mpack_start_map(writer, len(obj))
        for k, v in obj.items():
            mpack_write_utf8_cstr(writer, k)
            _dump(v, writer)
    elif t is int:
        mpack_write_int(writer, obj)
    elif t is float:
        mpack_write_double(writer, obj)
    elif t is bool:
        mpack_write_bool(writer, obj)
    elif t is str:
        mpack_write_utf8_cstr(writer, obj)
    elif t is bytes:
        mpack_write_bin(writer, obj, len(obj))
    elif obj is None:
        mpack_write_nil(writer)
    else:
        raise TypeError


def _load(reader, tag):
    mpack_read_tag_p(reader, tag)
    t = mpack_tag_type(tag)
    types = MpackType
    if t == types.nil:
        return None
    if t == types.bool:
        return mpack_tag_bool_value(tag)
    if t == types.int:
        return mpack_tag_int_value(tag)
    if t == types.uint:
        return mpack_tag_uint_value(tag)
    if t == types.float:
        return mpack_tag_float_value(tag)
    if t == types.double:
        return mpack_tag_double_value(tag)
    if t == types.str:
        count = mpack_tag_bytes(tag)
        p = mpack_read_utf8_inplace(reader, count)
        if not p:
            raise UnicodeError
        return ctypes.bytes_at(p, count).decode()
    if t == types.bin:
        count = mpack_tag_bytes(tag)
        p = mpack_read_bytes_inplace(reader, count)
        if not p:
            raise ValueError
        return ctypes.bytes_at(p, count)
    if t == types.array:
        count = mpack_tag_array_count(tag)
        r = []
        for _ in range(count):
            r.append(_load(reader, tag))
        mpack_done_array(reader)
        return r
    if t == types.map:
        count = mpack_tag_map_count(tag)
        r = {}
        for _ in range(count):
            key = _load(reader, tag)
            value = _load(reader, tag)
            r[key] = value
        mpack_done_map(reader)
        return r

    raise TypeError(t)
