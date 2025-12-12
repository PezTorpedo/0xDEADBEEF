# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

from typing import Any, Callable, Optional, Tuple

from hueutils.ctypes_adapter import ByReference

def decode_msg(msg: int) -> dict: ...

#  int mosquitto_lib_init(void)
def mosquitto_lib_init() -> int: ...

# int mosquitto_lib_cleanup(void)
def mosquitto_lib_cleanup() -> int: ...

# struct mosquitto *mosquitto_new(const char *id, bool clean_session, void *obj)
def mosquitto_new(id_: str, clean_session: bool, obj: Any) -> int: ...

# int mosquitto_will_set(struct mosquitto *mosq, const char *topic, int
# payloadlen, const void *payload, int qos, bool retain)
def mosquitto_will_set(mosq: int, topic: str, payload: str, qos: int, retain: bool) -> int: ...

# void mosquitto_destroy(struct mosquitto *mosq)
def mosquitto_destroy(mosq: int) -> None: ...

# int mosquitto_username_pw_set(struct mosquitto *mosq, const char *username, const char *password)
def mosquitto_username_pw_set(mosq: int, username: str, password: str) -> int: ...

# int mosquitto_connect(struct mosquitto *mosq, const char *host, int port, int keepalive)
def mosquitto_connect(mosq: int, host: str, port: int, keepalive: int) -> int: ...

# int mosquitto_disconnect(struct mosquitto *mosq)
def mosquitto_disconnect(mosq: int) -> int: ...

# int mosquitto_reconnect( struct mosquitto *mosq)
def mosquitto_reconnect(mosq: int) -> int: ...

# int mosquitto_publish(struct mosquitto *mosq, int *mid, const char
# *topic, int payloadlen, const void *payload, int qos, bool retain)
def mosquitto_publish(mosq: int, mid: Optional[int], topic: str, payload: str, qos: int, retain: bool) -> int: ...

# int mosquitto_subscribe(struct mosquitto *mosq, int *mid, const char *sub, int qos)
def mosquitto_subscribe(mosq: int, mid: Optional[int], sub: str, qos: int) -> int: ...

# int mosquitto_unsubscribe(struct mosquitto *mosq, int *mid, const char *sub)
def mosquitto_unsubscribe(mosq: int, mid: int, sub: str) -> int: ...

# int mosquitto_loop_forever(struct mosquitto *mosq, int timeout, int max_packets)
def mosquitto_loop_forever(mosq: int, timeout: int, max_packets: int) -> int: ...

# int mosquitto_loop_start(struct mosquitto *mosq)
def mosquitto_loop_start(mosq: int) -> int: ...

# int mosquitto_loop_stop(struct mosquitto *mosq, bool force)
def mosquitto_loop_stop(mosq: int, force: bool) -> int: ...

# int mosquitto_loop(struct mosquitto *mosq, int timeout, int max_packets)
def mosquitto_loop(mosq: int, timeout: int, max_packets: int) -> int: ...

# int mosquitto_socket(struct mosquitto *mosq)
def mosquitto_socket(mosq: int) -> int: ...

# void mosquitto_user_data_set(struct mosquitto *mosq, void *obj)
def mosquitto_user_data_set(mosq: int, obj: Any) -> None: ...

# void *mosquitto_userdata(struct mosquitto *mosq)
def mosquitto_userdata(mosq: int) -> None: ...

# void mosquitto_connect_callback_set(struct mosquitto *mosq, void (*on_connect)(struct mosquitto *, void *, int))
def mosquitto_connect_callback_set(
    mosq: int, cb: Callable[[int, Any, int], None]
) -> Tuple[int, Callable[[int, Any, int], None]]: ...

# void mosquitto_disconnect_callback_set(struct mosquitto *mosq, void (*on_disconnect)(struct mosquitto *, void *, int))
def mosquitto_disconnect_callback_set(
    mosq: int, cb: Callable[[int, Any, int], None]
) -> Tuple[int, Callable[[int, Any, int], None]]: ...

# void mosquitto_message_callback_set(struct mosquitto *mosq, void
# (*on_message)(struct mosquitto *, void *, const struct mosquitto_message
# *))
def mosquitto_message_callback_set(
    mosq: int, cb: Callable[[int, Any, int], None]
) -> Tuple[int, Callable[[int, Any, int], None]]: ...

# void mosquitto_log_callback_set(struct mosquitto *mosq, void (*on_log)(struct mosquitto *, void *, int, const char *))
def mosquitto_log_callback_set(mosq: int, cb: Callable[[int, Any, int, str], None]) -> None: ...

# int mosquitto_topic_matches_sub(const char *sub, const char *topic, bool *result)
def mosquitto_topic_matches_sub(sub: str, topic: str, result: ByReference) -> int: ...
