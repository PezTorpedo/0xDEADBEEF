# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

import ffi
import uctypes as ctypes

from hueutils.c_functions import strlen
from hueutils.ctypes_adapter import _int_size
from hueutils.retval_exception import must_not_return, must_return

_mosquitto = ffi.open("libmosquitto.so")

MOSQ_ERR_SUCCESS = 0
MOSQ_ERR_ERRNO = 14

INT_TYPE = ctypes.UINT64 if _int_size == 8 else ctypes.UINT32

_mosquitto_message_t = {
    "mid": 0 * _int_size | INT_TYPE,
    "topic": 1 * _int_size | INT_TYPE,
    "payload": 2 * _int_size | INT_TYPE,
    "payloadlen": 3 * _int_size | INT_TYPE,
    "qos": 4 * _int_size | INT_TYPE,
    "retain": 5 * _int_size | INT_TYPE,
}


class MqttError(Exception):
    pass


def decode_msg(msg):
    o = ctypes.struct(msg, _mosquitto_message_t)

    assert o.topic
    assert o.payload

    topic_len = strlen(o.topic)
    topic = ctypes.bytes_at(o.topic, topic_len)

    return {
        "mid": o.mid,
        "topic": topic,
        "payload": ctypes.bytes_at(o.payload, o.payloadlen),
        "qos": o.qos,
        "retain": bool(o.retain),
    }


#  int mosquitto_lib_init(void)
_mosquitto_lib_init = must_return(MOSQ_ERR_SUCCESS, _mosquitto.func("i", "mosquitto_lib_init", ""), MqttError)

_mosquitto_lib_init()  # start the library right away

# int mosquitto_lib_cleanup(void)
mosquitto_lib_cleanup = must_return(MOSQ_ERR_SUCCESS, _mosquitto.func("i", "mosquitto_lib_cleanup", ""), MqttError)

# struct mosquitto *mosquitto_new(const char *id, bool clean_session, void *obj)
mosquitto_new = must_not_return(None, _mosquitto.func("p", "mosquitto_new", "sip"), MqttError)

# int mosquitto_will_set(struct mosquitto *mosq, const char *topic, int
# payloadlen, const void *payload, int qos, bool retain)
mosquitto_will_set = must_return(MOSQ_ERR_SUCCESS, _mosquitto.func("i", "mosquitto_will_set", "psiPii"), MqttError)

# void mosquitto_destroy(struct mosquitto *mosq)
mosquitto_destroy = _mosquitto.func("v", "mosquitto_destroy", "p")

# int mosquitto_username_pw_set(struct mosquitto *mosq, const char *username, const char *password)
mosquitto_username_pw_set = must_return(
    MOSQ_ERR_SUCCESS, _mosquitto.func("i", "mosquitto_username_pw_set", "pss"), MqttError
)

# int mosquitto_connect(struct mosquitto *mosq, const char *host, int port, int keepalive)
mosquitto_connect = must_return(MOSQ_ERR_SUCCESS, _mosquitto.func("i", "mosquitto_connect", "psii"), MqttError)

# int mosquitto_disconnect(struct mosquitto *mosq)
mosquitto_disconnect = must_return(MOSQ_ERR_SUCCESS, _mosquitto.func("i", "mosquitto_disconnect", "p"), MqttError)

# int mosquitto_publish(struct mosquitto *mosq, int *mid, const char
# *topic, int payloadlen, const void *payload, int qos, bool retain)
mosquitto_publish = must_return(MOSQ_ERR_SUCCESS, _mosquitto.func("i", "mosquitto_publish", "ppsiPii"), MqttError)

# int mosquitto_subscribe(struct mosquitto *mosq, int *mid, const char *sub, int qos)
mosquitto_subscribe = must_return(MOSQ_ERR_SUCCESS, _mosquitto.func("i", "mosquitto_subscribe", "ppsi"), MqttError)

# int mosquitto_unsubscribe(struct mosquitto *mosq, int *mid, const char *sub)
mosquitto_unsubscribe = must_return(MOSQ_ERR_SUCCESS, _mosquitto.func("i", "mosquitto_unsubscribe", "pps"), MqttError)

# int mosquitto_loop_forever(struct mosquitto *mosq, int timeout, int max_packets)
mosquitto_loop_forever = must_return(MOSQ_ERR_SUCCESS, _mosquitto.func("i", "mosquitto_loop_forever", "pii"), MqttError)

# int mosquitto_loop_start(struct mosquitto *mosq)
mosquitto_loop_start = must_return(MOSQ_ERR_SUCCESS, _mosquitto.func("i", "mosquitto_loop_start", "p"), MqttError)

# int mosquitto_loop_stop(struct mosquitto *mosq, bool force)
mosquitto_loop_stop = must_return(MOSQ_ERR_SUCCESS, _mosquitto.func("i", "mosquitto_loop_stop", "pi"), MqttError)

# int mosquitto_loop(struct mosquitto *mosq, int timeout, int max_packets)
mosquitto_loop = must_return(MOSQ_ERR_SUCCESS, _mosquitto.func("i", "mosquitto_loop", "pii"), MqttError)

# int mosquitto_socket(struct mosquitto *mosq)
mosquitto_socket = must_not_return(0, _mosquitto.func("i", "mosquitto_socket", "p"), MqttError)

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
mosquitto_disconnect_callback_set = _mosquitto.func("v", "mosquitto_disconnect_callback_set", "pC")

# void mosquitto_message_callback_set(struct mosquitto *mosq, void
# (*on_message)(struct mosquitto *, void *, const struct mosquitto_message
# *))
_mosquitto_message_callback_set = _mosquitto.func("v", "mosquitto_message_callback_set", "pC")


def mosquitto_message_callback_set(mosq, cb):
    wrapped_cb = ffi.callback("v", cb, "ppp")
    _mosquitto_message_callback_set(mosq, wrapped_cb)

    return wrapped_cb, cb  # this must be stored somewhere to avoid garbage collection


# void mosquitto_log_callback_set(struct mosquitto *mosq, void (*on_log)(struct mosquitto *, void *, int, const char *))
mosquitto_log_callback_set = _mosquitto.func("v", "mosquitto_log_callback_set", "pC")

# int mosquitto_topic_matches_sub(const char *sub, const char *topic, bool *result)
mosquitto_topic_matches_sub = must_return(
    MOSQ_ERR_SUCCESS, _mosquitto.func("i", "mosquitto_topic_matches_sub", "ssp"), MqttError
)
