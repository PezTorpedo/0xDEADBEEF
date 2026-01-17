# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

from sys import atexit

import ffi
import uctypes
from util.curl.ffex import LONG, LONG_LONG, NULL, Reference, native, native_64_bit, native_argument_out

# Miscellaneous CURL constants.
CURLE_OK = 0
CURLE_OUT_OF_MEMORY = 27
CURLE_SSL_CONNECT_ERROR = 35
CURL_SOCKET_TIMEOUT = -1
CURL_WRITEFUNC_PAUSE = 0x10000001

# curl_global_init flags.
_CURL_GLOBAL_SSL = 1 << 0
_CURL_GLOBAL_WIN32 = 1 << 1
_CURL_GLOBAL_ALL = _CURL_GLOBAL_SSL | _CURL_GLOBAL_WIN32
_CURL_GLOBAL_DEFAULT = _CURL_GLOBAL_ALL

# curl_easy_pause flags.
CURLPAUSE_RECV = 1 << 0
CURLPAUSE_RECV_CONT = 0
CURLPAUSE_SEND = 1 << 2
CURLPAUSE_SEND_CONT = 0
CURLPAUSE_ALL = CURLPAUSE_RECV | CURLPAUSE_SEND
CURLPAUSE_CONT = CURLPAUSE_RECV_CONT | CURLPAUSE_SEND_CONT

# Type offsets for CURL option constants.
CURLOPTTYPE_BASE = 10000
CURLOPTTYPE_LONG = 0
CURLOPTTYPE_OBJECTPOINT = 1
CURLOPTTYPE_FUNCTIONPOINT = 2
CURLOPTTYPE_OFF_T = 3
CURLOPTTYPE_BLOB = 4

# curl_easy_setopt options.
CURLOPT_WRITEDATA = CURLOPTTYPE_BASE * CURLOPTTYPE_OBJECTPOINT + 1
CURLOPT_URL = CURLOPTTYPE_BASE * CURLOPTTYPE_OBJECTPOINT + 2
CURLOPT_WRITEFUNCTION = CURLOPTTYPE_BASE * CURLOPTTYPE_FUNCTIONPOINT + 11
CURLOPT_LOW_SPEED_LIMIT = CURLOPTTYPE_BASE * CURLOPTTYPE_LONG + 19
CURLOPT_LOW_SPEED_TIME = CURLOPTTYPE_BASE * CURLOPTTYPE_LONG + 20
CURLOPT_VERBOSE = CURLOPTTYPE_BASE * CURLOPTTYPE_LONG + 41
CURLOPT_FOLLOWLOCATION = CURLOPTTYPE_BASE * CURLOPTTYPE_LONG + 52
CURLOPT_SSL_VERIFYPEER = CURLOPTTYPE_BASE * CURLOPTTYPE_LONG + 64
CURLOPT_CAINFO = CURLOPTTYPE_BASE * CURLOPTTYPE_OBJECTPOINT + 65
CURLOPT_MAXREDIRS = CURLOPTTYPE_BASE * CURLOPTTYPE_LONG + 68
CURLOPT_SSL_VERIFYHOST = CURLOPTTYPE_BASE * CURLOPTTYPE_LONG + 81
CURLOPT_BUFFERSIZE = CURLOPTTYPE_BASE * CURLOPTTYPE_LONG + 98
CURLOPT_TCP_NODELAY = CURLOPTTYPE_BASE * CURLOPTTYPE_LONG + 121

# curl_multi_setopt options.
CURLMOPT_SOCKETFUNCTION = CURLOPTTYPE_BASE * CURLOPTTYPE_FUNCTIONPOINT + 1
CURLMOPT_SOCKETDATA = CURLOPTTYPE_BASE * CURLOPTTYPE_OBJECTPOINT + 2
CURLMOPT_TIMERFUNCTION = CURLOPTTYPE_BASE * CURLOPTTYPE_FUNCTIONPOINT + 4
CURLMOPT_TIMERDATA = CURLOPTTYPE_BASE * CURLOPTTYPE_OBJECTPOINT + 5

# Type offsets for CURL info constants.
CURLINFO_TYPEMASK = 0xF00000
CURLINFO_LONG = 0x200000
CURLINFO_OFF_T = 0x600000

# curl_easy_getinfo infos.
CURLINFO_RESPONSE_CODE = CURLINFO_LONG + 2
CURLINFO_OS_ERRNO = CURLINFO_LONG + 25
CURLINFO_CONTENT_LENGTH_DOWNLOAD_T = CURLINFO_OFF_T + 15

# CURLMOPT_SOCKETFUNCTION flag bits.
CURL_POLL_NONE = 0
CURL_POLL_IN = 1
CURL_POLL_OUT = 2
CURL_POLL_INOUT = 3
CURL_POLL_REMOVE = 4

# curl_multi_socket_action event bits.
CURL_CSELECT_IN = 1
CURL_CSELECT_OUT = 2
CURL_CSELECT_ERR = 4

# CURLMsg native layout.
__CURLMSG_SPEC = {
    "msg": uctypes.UINT32 | 0,
    "easy_handle": uctypes.PTR | (8 if native_64_bit() else 4),
    "result": uctypes.UINT32 | (16 if native_64_bit() else 8),
}


# fmt: off
@native(dlib="libcurl.so.4", returns="s", arguments="i")
def curl_easy_strerror(curlcode: int) -> str:
    pass


@native(dlib="libcurl.so.4", returns="s", arguments="i")
def curl_multi_strerror(curlmcode: int) -> str:
    pass


@native(dlib="libcurl.so.4", returns="i", must_return=CURLE_OK, arguments="i", name="curl_global_init", decoder=curl_easy_strerror)
def _curl_global_init(flags: int) -> int:
    """Must be called once when the program starts."""
    pass


@native(dlib="libcurl.so.4", name="curl_global_cleanup")
def _curl_global_cleanup():
    """Must be called once when the program exits."""
    pass


@native(dlib="libcurl.so.4", returns="p", must_not_return=NULL, die_on_error=True)
def curl_easy_init() -> int:
    pass


@native(dlib="libcurl.so.4", arguments="p")
def curl_easy_cleanup(easy_handle: int):
    pass


@native(dlib="libcurl.so.4", returns="i", must_return=CURLE_OK, arguments="pi", decoder=curl_easy_strerror)
def curl_easy_pause(easy_handle: int, flags: int):
    pass


@native(dlib="libcurl.so.4", returns="i", must_return=CURLE_OK, arguments="pii", name="curl_easy_setopt", decoder=curl_easy_strerror)
def __curl_easy_setopt_i(easy_handle: int, option: int, value: int):
    pass


@native(dlib="libcurl.so.4", returns="i", must_return=CURLE_OK, arguments="pip", name="curl_easy_setopt", decoder=curl_easy_strerror)
def __curl_easy_setopt_p(easy_handle: int, option: int, pointer):
    pass


def curl_easy_setopt(easy_handle: int, option: int, value):
    if value is None:
        return
    if option // CURLOPTTYPE_BASE == CURLOPTTYPE_LONG:
        return __curl_easy_setopt_i(easy_handle, option, int(value))
    if option // CURLOPTTYPE_BASE == CURLOPTTYPE_OBJECTPOINT:
        return __curl_easy_setopt_p(easy_handle, option, value)
    if option // CURLOPTTYPE_BASE == CURLOPTTYPE_FUNCTIONPOINT:
        return __curl_easy_setopt_p(easy_handle, option, value)
    raise TypeError(f"unsupported type for easy option {option}")


@native_argument_out(of_type=LONG)
@native(dlib="libcurl.so.4", returns="i", must_return=CURLE_OK, arguments="pip", name="curl_easy_getinfo", decoder=curl_easy_strerror)
def __curl_easy_getinfo_i(easy_handle: int, info: int) -> int:
    pass


@native_argument_out(of_type=LONG_LONG)
@native(dlib="libcurl.so.4", returns="i", must_return=CURLE_OK, arguments="pip", name="curl_easy_getinfo", decoder=curl_easy_strerror)
def __curl_easy_getinfo_ll(easy_handle: int, info: int) -> int:
    pass


def curl_easy_getinfo(easy_handle: int, info: int) -> int:
    if info & CURLINFO_TYPEMASK == CURLINFO_LONG:
        return __curl_easy_getinfo_i(easy_handle, info)
    if info & CURLINFO_TYPEMASK == CURLINFO_OFF_T:
        return __curl_easy_getinfo_ll(easy_handle, info)
    raise TypeError(f"unsupported type for easy info 0x{info:x}")


@native(dlib="libcurl.so.4", returns="p", must_not_return=NULL, die_on_error=True)
def curl_multi_init() -> int:
    pass


@native(dlib="libcurl.so.4", returns="i", must_return=CURLE_OK, arguments="p", decoder=curl_multi_strerror)
def curl_multi_cleanup(multi_handle: int):
    pass


@native(dlib="libcurl.so.4", returns="i", must_return=CURLE_OK, arguments="pp", decoder=curl_multi_strerror)
def curl_multi_add_handle(multi_handle: int, easy_handle: int):
    pass


@native(dlib="libcurl.so.4", returns="i", must_return=CURLE_OK, arguments="pp", decoder=curl_multi_strerror)
def curl_multi_remove_handle(multi_handle: int, easy_handle: int):
    pass


@native(dlib="libcurl.so.4", returns="i", must_return=CURLE_OK, arguments="pip", name="curl_multi_setopt", decoder=curl_multi_strerror)
def __curl_multi_setopt_p(multi_handle: int, option: int, pointer):
    pass


def curl_multi_setopt(multi_handle: int, option: int, value):
    if option // CURLOPTTYPE_BASE == CURLOPTTYPE_OBJECTPOINT:
        return __curl_multi_setopt_p(multi_handle, option, value)
    if option // CURLOPTTYPE_BASE == CURLOPTTYPE_FUNCTIONPOINT:
        return __curl_multi_setopt_p(multi_handle, option, value)
    raise TypeError(f"unsupported type for multi option {option}")


@native_argument_out(of_type=LONG)
@native(dlib="libcurl.so.4", returns="i", must_return=CURLE_OK, arguments="piip", decoder=curl_multi_strerror)
def curl_multi_socket_action(multi_handle: int, socket: int, event_bitmask: int) -> int:
    pass


@native(dlib="libcurl.so.4", returns="p", arguments="pp", name="curl_multi_info_read")
def __curl_multi_info_read(multi_handle: int, reference: int) -> int:
    pass


def curl_multi_info_read(multi_handle: int) -> tuple:
    msgs_in_queue = Reference(LONG)
    if curl_msg := __curl_multi_info_read(multi_handle, msgs_in_queue):
        return uctypes.struct(curl_msg, __CURLMSG_SPEC)
    return None


def wrap_socket_callback(cb):
    return ffi.callback("i", cb, "piipp")


def wrap_timer_callback(cb):
    return ffi.callback("i", cb, "pip")


@native(dlib="libcurlaux.so", returns="p", must_not_return=NULL, arguments="Ippp", name="Curlaux_attach")
def curlaux_attach(buffer_size: int, easy_handle: int, user_handle: int, data_callback) -> int:
    pass


@native(dlib="libcurlaux.so", returns="I", arguments="p", name="Curlaux_get_length")
def curlaux_get_length(curlaux: int) -> int:
    pass


@native(dlib="libcurlaux.so", returns="p", arguments="p", name="Curlaux_get_data")
def curlaux_get_data(curlaux: int) -> int:
    pass


@native(dlib="libcurlaux.so", arguments="p", name="Curlaux_clean")
def curlaux_clean(curlaux: int):
    pass


@native(dlib="libcurlaux.so", arguments="p", name="Curlaux_detach")
def curlaux_detach(curlaux: int):
    pass


def wrap_data_callback(cb):
    return ffi.callback("i", cb, "p")


_curl_global_init(_CURL_GLOBAL_DEFAULT)
atexit(_curl_global_cleanup)
