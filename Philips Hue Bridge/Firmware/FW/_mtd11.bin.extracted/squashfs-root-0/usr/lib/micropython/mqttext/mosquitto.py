# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

import ffi
import uctypes as ctypes

from hueutils.c_functions import strlen
from hueutils.ctypes_adapter import _int_size
from hueutils.retval_exception import must_not_return, must_return

from .constants import MOSQ_ERR_SUCCESS
from .exceptions import MqttError

_mosquitto = ffi.open("libmosquitto.so")


INT_TYPE = ctypes.UINT64 if _int_size == 8 else ctypes.UINT32

_mosquitto_message_t = {
    "mid": 0 * _int_size | INT_TYPE,
    "topic": 1 * _int_size | INT_TYPE,
    "payload": 2 * _int_size | INT_TYPE,
    "payloadlen": 3 * _int_size | ctypes.UINT32,
    "qos": (3 * _int_size + 4) | ctypes.UINT32,
    "retain": (3 * _int_size + 8) | ctypes.UINT32,
}


def decode_msg(msg):
    o = ctypes.struct(msg, _mosquitto_message_t)

    assert o.topic, "Incoming message with no topic"

    topic_len = strlen(o.topic)
    topic = ctypes.bytes_at(o.topic, topic_len)

    return {
        "mid": o.mid,
        "topic": topic,
        "payload": ctypes.bytes_at(o.payload, o.payloadlen) if o.payload else None,
        "qos": o.qos,
        "retain": bool(o.retain),
    }


#  int mosquitto_lib_init(void)
_mosquitto_lib_init = must_return(MOSQ_ERR_SUCCESS, _mosquitto.func("i", "mosquitto_lib_init", ""), MqttError)

_mosquitto_lib_init()  # start the library right away

# int mosquitto_lib_cleanup(void)
mosquitto_lib_cleanup = must_return(MOSQ_ERR_SUCCESS, _mosquitto.func("i", "mosquitto_lib_cleanup", ""), MqttError)

# struct mosquitto *mosquitto_new(const char *id, bool clean_session, void *obj)
_mosquitto_new = must_not_return(None, _mosquitto.func("p", "mosquitto_new", "sip"), MqttError)


def mosquitto_new(id_, clean_session, obj):
    return _mosquitto_new(id_, int(bool(clean_session)), obj)


# int mosquitto_will_set(struct mosquitto *mosq, const char *topic, int
# payloadlen, const void *payload, int qos, bool retain)
_mosquitto_will_set = must_return(MOSQ_ERR_SUCCESS, _mosquitto.func("i", "mosquitto_will_set", "psiPii"), MqttError)


def mosquitto_will_set(mosq, topic, payload, qos, retain):
    return _mosquitto_will_set(mosq, topic, len(payload), payload, qos, int(bool(retain)))


# void mosquitto_destroy(struct mosquitto *mosq)
mosquitto_destroy = _mosquitto.func("v", "mosquitto_destroy", "p")

# int mosquitto_username_pw_set(struct mosquitto *mosq, const char *username, const char *password)
mosquitto_username_pw_set = must_return(
    MOSQ_ERR_SUCCESS, _mosquitto.func("i", "mosquitto_username_pw_set", "pss"), MqttError
)

# int mosquitto_connect(struct mosquitto *mosq, const char *host, int port, int keepalive)
mosquitto_connect = _mosquitto.func("i", "mosquitto_connect", "psii")

# int mosquitto_disconnect(struct mosquitto *mosq)
mosquitto_disconnect = must_return(MOSQ_ERR_SUCCESS, _mosquitto.func("i", "mosquitto_disconnect", "p"), MqttError)

# int mosquitto_reconnect( struct mosquitto *mosq)
mosquitto_reconnect = _mosquitto.func("i", "mosquitto_reconnect", "p")

# int mosquitto_publish(struct mosquitto *mosq, int *mid, const char
# *topic, int payloadlen, const void *payload, int qos, bool retain)
_mosquitto_publish = _mosquitto.func("i", "mosquitto_publish", "ppsiPii")


def mosquitto_publish(mosq, mid, topic, payload, qos, retain):
    return _mosquitto_publish(mosq, mid, topic, len(payload), payload, qos, int(bool(retain)))


# int mosquitto_subscribe(struct mosquitto *mosq, int *mid, const char *sub, int qos)
mosquitto_subscribe = _mosquitto.func("i", "mosquitto_subscribe", "ppsi")

# int mosquitto_unsubscribe(struct mosquitto *mosq, int *mid, const char *sub)
mosquitto_unsubscribe = must_return(MOSQ_ERR_SUCCESS, _mosquitto.func("i", "mosquitto_unsubscribe", "pps"), MqttError)

# int mosquitto_loop_forever(struct mosquitto *mosq, int timeout, int max_packets)
mosquitto_loop_forever = must_return(MOSQ_ERR_SUCCESS, _mosquitto.func("i", "mosquitto_loop_forever", "pii"), MqttError)

# int mosquitto_loop_start(struct mosquitto *mosq)
mosquitto_loop_start = must_return(MOSQ_ERR_SUCCESS, _mosquitto.func("i", "mosquitto_loop_start", "p"), MqttError)

# int mosquitto_loop_stop(struct mosquitto *mosq, bool force)
_mosquitto_loop_stop = must_return(MOSQ_ERR_SUCCESS, _mosquitto.func("i", "mosquitto_loop_stop", "pi"), MqttError)


def mosquitto_loop_stop(mosq, force=False):
    return _mosquitto_loop_stop(mosq, int(bool(force)))


# int mosquitto_loop(struct mosquitto *mosq, int timeout, int max_packets)
mosquitto_loop = _mosquitto.func("i", "mosquitto_loop", "pii")

# int mosquitto_socket(struct mosquitto *mosq)
mosquitto_socket = must_not_return(-1, _mosquitto.func("i", "mosquitto_socket", "p"), MqttError)

# void mosquitto_user_data_set(struct mosquitto *mosq, void *obj)
mosquitto_user_data_set = _mosquitto.func("v", "mosquitto_user_data_set", "pp")

# void *mosquitto_userdata(struct mosquitto *mosq)
mosquitto_userdata = must_not_return(None, _mosquitto.func("p", "mosquitto_userdata", "p"), MqttError)

# void mosquitto_connect_callback_set(struct mosquitto *mosq, void (*on_connect)(struct mosquitto *, void *, int))
_mosquitto_connect_callback_set = _mosquitto.func("v", "mosquitto_connect_callback_set", "pC")


def mosquitto_connect_callback_set(mosq, cb):
    wrapped_cb = ffi.callback("v", cb, "ppi")
    _mosquitto_connect_callback_set(mosq, wrapped_cb)

    return wrapped_cb, cb  # this must be stored somewhere to avoid garbage collection


# void mosquitto_disconnect_callback_set(struct mosquitto *mosq, void (*on_disconnect)(struct mosquitto *, void *, int))
_mosquitto_disconnect_callback_set = _mosquitto.func("v", "mosquitto_disconnect_callback_set", "pC")


def mosquitto_disconnect_callback_set(mosq, cb):
    wrapped_cb = ffi.callback("v", cb, "ppi")
    _mosquitto_disconnect_callback_set(mosq, wrapped_cb)

    return wrapped_cb, cb  # this must be stored somewhere to avoid garbage collection


# void mosquitto_message_callback_set(struct mosquitto *mosq, void
# (*on_message)(struct mosquitto *, void *, const struct mosquitto_message
# *))
_mosquitto_message_callback_set = _mosquitto.func("v", "mosquitto_message_callback_set", "pC")


def mosquitto_message_callback_set(mosq, cb):
    wrapped_cb = ffi.callback("v", cb, "ppp")
    _mosquitto_message_callback_set(mosq, wrapped_cb)

    return wrapped_cb, cb  # this must be stored somewhere to avoid garbage collection


# void mosquitto_log_callback_set(struct mosquitto *mosq, void (*on_log)(struct mosquitto *, void *, int, const char *))
_mosquitto_log_callback_set = _mosquitto.func("v", "mosquitto_log_callback_set", "pC")


def mosquitto_log_callback_set(mosq, cb):
    wrapped_cb = ffi.callback("v", cb, "ppip")
    _mosquitto_log_callback_set(mosq, wrapped_cb)

    return wrapped_cb, cb  # this must be stored somewhere to avoid garbage collection


# int mosquitto_topic_matches_sub(const char *sub, const char *topic, bool *result)
mosquitto_topic_matches_sub = must_return(
    MOSQ_ERR_SUCCESS, _mosquitto.func("i", "mosquitto_topic_matches_sub", "ssp"), MqttError
)
