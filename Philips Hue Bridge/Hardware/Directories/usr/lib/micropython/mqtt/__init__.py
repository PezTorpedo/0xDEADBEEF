# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

import uasyncio as asyncio

from hueutils.ctypes_adapter import ByReference
from hueutils.queue import Queue
from mqtt.mosquitto import (
    decode_msg,
    mosquitto_connect,
    mosquitto_destroy,
    mosquitto_loop,
    mosquitto_message_callback_set,
    mosquitto_new,
    mosquitto_publish,
    mosquitto_socket,
    mosquitto_subscribe,
    mosquitto_topic_matches_sub,
    mosquitto_username_pw_set,
    mosquitto_will_set,
)


class _Subscription:
    def __aiter__(self):
        self._ev = Queue()
        return self

    async def __anext__(self):
        return await self._ev.get()

    def send(self, msg):
        self._ev.put(msg)


class Mqtt:
    def __init__(self, clientid, username=None, password=None, hostname="localhost", port=1883, keepalive=60):
        self._hostname = hostname
        self._port = port
        self._keepalive = keepalive

        self._mqtt = mosquitto_new(clientid, 1, None)
        mosquitto_username_pw_set(self._mqtt, username, password)

        # return value must be stored to avoid it being garbage collected
        self._msg_cb = mosquitto_message_callback_set(self._mqtt, self._on_message)

        self._subscriptions = {}

    async def __aenter__(self):
        mosquitto_connect(self._mqtt, self._hostname, self._port, self._keepalive)
        self.worker_task = asyncio.create_task(self._incoming_loop())
        return self

    async def __aexit__(self, exc_type, exc, tb):
        mosquitto_destroy(self._mqtt)

    def _on_message(self, mosq, ctx, msg):
        m = decode_msg(msg)
        match = ByReference()
        for sub, o in self._subscriptions.items():
            mosquitto_topic_matches_sub(sub, m["topic"], match)
            if bool(match):
                o.send(m)

    async def _incoming_loop(self):
        async def wait_for_data():
            yield asyncio.core._io_queue.queue_read(mosquitto_socket(self._mqtt))  # pylint: disable=protected-access

        while True:
            try:
                # do not block forever, so mosquitto_loop can be called to handle PINGREQ
                await asyncio.wait_for(wait_for_data(), 5)
            except asyncio.TimeoutError:
                pass
            mosquitto_loop(self._mqtt, 1, 1)

    def publish(self, topic, message, QoS=0, retain=False):
        mosquitto_publish(self._mqtt, None, topic, len(message), message, QoS, 1 if retain else 0)

    def will_set(self, topic, message, QoS=0, retain=False):
        mosquitto_will_set(self._mqtt, topic, len(message), message, QoS, 1 if retain else 0)

    def subscribe(self, subscription, QoS=0):
        mosquitto_subscribe(self._mqtt, None, subscription, QoS)
        s = _Subscription(self._mqtt, subscription, QoS)
        self._subscriptions[subscription] = s
        return s
