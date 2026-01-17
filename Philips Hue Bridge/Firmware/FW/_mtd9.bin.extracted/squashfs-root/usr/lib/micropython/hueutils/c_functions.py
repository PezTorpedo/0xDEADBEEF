# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

import ffi

try:
    _libc = ffi.open("libc.so.6")  # Ubuntu and OpenWRT (musl)
except BaseException:
    _libc = ffi.open("libc.so.1")  # QSDK (uclibc)

strlen = _libc.func("i", "strlen", "s")
getenv = _libc.func("s", "getenv", "s")
fsync = _libc.func("i", "fsync", "i")
flock = _libc.func("i", "flock", "ii")
