import asyncio

import uos as os

from hueutils.ctypes_adapter import ByReference

from .constants import MOSQ_ERR_ERRNO, MOSQ_ERR_SUCCESS, TIMEOUT_LOOP, TIMEOUT_RECONNECT
from .mosquitto import (
    decode_msg,
    mosquitto_connect,
    mosquitto_connect_callback_set,
    mosquitto_destroy,
    mosquitto_disconnect,
    mosquitto_disconnect_callback_set,
    mosquitto_loop,
    mosquitto_message_callback_set,
    mosquitto_new,
    mosquitto_publish,
    mosquitto_reconnect,
    mosquitto_socket,
    mosquitto_subscribe,
    mosquitto_topic_matches_sub,
    mosquitto_username_pw_set,
    mosquitto_will_set,
)
from .subscription import Subscription


class MqttExt:
    def __init__(
        self,
        clientid,
        username=None,
        password=None,
        postinitcall=None,
        hostname="localhost",
        port=1883,
        keepalive=60,
        connect_callback=None,
    ):
        self._clientid = clientid
        self._username = username
        self._password = password
        self._hostname = hostname
        self._port = port
        self._keepalive = keepalive
        self._broker_connected = False
        self._connect_count = 0
        self._connect_callback = connect_callback

        self._mqtt = mosquitto_new(self._clientid, 0, None)
        mosquitto_username_pw_set(self._mqtt, self._username, self._password)

        # return value must be stored to avoid it being garbage collected
        self._msg_cb = mosquitto_message_callback_set(self._mqtt, self._on_message)
        self._connect_cb = mosquitto_connect_callback_set(self._mqtt, self._on_connect)
        self._disconnect_cb = mosquitto_disconnect_callback_set(self._mqtt, self._on_disconnect)

        self._subscriptions = {}

        if postinitcall is not None:
            # pass postinitcall callback to perform will_set that should be called between mosquitto_new and mosquitto_connect
            postinitcall(self)

    async def __aenter__(self):
        rc = mosquitto_connect(self._mqtt, self._hostname, self._port, self._keepalive)
        if rc != MOSQ_ERR_SUCCESS:
            print(f"MqttExt:__aenter__: mosquitto_connect failed, rc={rc}")
        self.worker_task = asyncio.create_task(self._incoming_loop())
        return self

    async def __aexit__(self, exc_type, exc, tb):
        mosquitto_disconnect(self._mqtt)
        mosquitto_destroy(self._mqtt)

    def _on_message(self, mosq, ctx, msg):
        m = decode_msg(msg)
        match = ByReference()
        for sub, o in self._subscriptions.items():
            mosquitto_topic_matches_sub(sub, m["topic"], match)
            if bool(match):
                o.send(m)

    def _on_connect(self, mosq, ctx, rc):
        # recover subscription topics that we have
        for key, value in self._subscriptions.items():
            mosquitto_subscribe(self._mqtt, None, key, value.qos)
        self._broker_connected = True
        if self._connect_callback is not None:
            self._connect_count += 1
            self._connect_callback(self._connect_count)

    def _on_disconnect(self, mosq, ctx, rc):
        self._broker_connected = False
        self.mosq_err_log("_on_disconnect", rc)

    # Recommended to be used right after failed mosquitto lib calls to
    # avoid errno overwriting.
    def mosq_err_log(self, msg, mosq_rc):
        errno_str = f"MqttExt:{msg}: rc = {mosq_rc}"
        if mosq_rc == MOSQ_ERR_ERRNO:
            errno_str += f", errno = {os.errno()}"
        print(errno_str)

    async def _incoming_loop(self):
        async def wait_for_data():
            yield asyncio.core._io_queue.queue_read(mosquitto_socket(self._mqtt))  # pylint: disable=protected-access

        while True:
            need_reconnect = False
            try:
                # do not block forever, so mosquitto_loop can be called to handle PINGREQ
                await asyncio.wait_for(wait_for_data(), TIMEOUT_LOOP)
            except asyncio.TimeoutError:
                pass
            except Exception:
                need_reconnect = True

            rc = mosquitto_loop(self._mqtt, 1, 1)
            if rc != MOSQ_ERR_SUCCESS or need_reconnect:
                # connection lost
                await asyncio.sleep(TIMEOUT_RECONNECT)
                try:
                    await asyncio.wait_for(self.reconnect(), TIMEOUT_RECONNECT)
                except asyncio.TimeoutError:
                    pass

    async def reconnect(self):
        rc = mosquitto_reconnect(self._mqtt)
        if rc != MOSQ_ERR_SUCCESS:
            self.mosq_err_log("mosquitto_reconnect failed", rc)

    def publish(self, topic, message, qos=0, retain=False):
        rc = mosquitto_publish(self._mqtt, None, topic, message, qos, retain)
        if rc != MOSQ_ERR_SUCCESS:
            self.mosq_err_log("publish: mosquitto_publish failed", rc)

    # According to the documentation for libMosquitto a will might be set up, but it needs to be done before connection
    # Use postinitcall for it, in case of using as async object
    def will_set(self, topic, message, qos=0, retain=False):
        mosquitto_will_set(self._mqtt, topic, message, qos, retain)

    def subscribe(self, subscription, qos=0):
        s = Subscription(self._mqtt, subscription, qos)
        self._subscriptions[subscription] = s
        if self._broker_connected:
            rc = mosquitto_subscribe(self._mqtt, None, subscription, qos)
            if rc != MOSQ_ERR_SUCCESS:
                self.mosq_err_log("subscribe: mosquitto_subscribe failed", rc)
        return s
