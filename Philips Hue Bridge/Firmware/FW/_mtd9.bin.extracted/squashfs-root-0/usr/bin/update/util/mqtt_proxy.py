# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

from mqttext import MqttError, MqttExt  # NOQA


class MqttProxy(MqttExt):
    def __init__(self, clientid=None, hostname=None, port=None, postinitcall=None, connect_callback=None):
        global __instance
        assert __instance is None, "Only one instance of MqttProxy can be created"
        super().__init__(
            clientid=clientid,
            hostname=hostname,
            port=port,
            postinitcall=postinitcall,
            connect_callback=connect_callback,
        )
        self.__iot_connected = False
        __instance = self

    def iot_connected(self, connected: bool):
        self.__iot_connected = connected
        __push_report_queue()


__instance: MqttProxy = None
__publish_queue = []
__publish_queue_reports = []


def mqtt_publish(topic: str, message, qos=0, retain=False):
    """
    Publishes a MQTT message. Can be called before the connection is up,
    in which case the message will be queued. And also can be called for sending report before the
    iot connection is established in which case the message will be queued untill __iot_connected flag is set up.
    """
    if topic == "iot/out/otau":
        if __instance is not None and __instance.__iot_connected:
            __push_report_queue()
            __instance.publish(topic, message, qos, retain)
        else:
            __publish_queue_reports.append((topic, message, qos, retain))
    else:
        if __instance is not None and __instance._broker_connected:
            __push_queue()
            __instance.publish(topic, message, qos, retain)
        else:
            __publish_queue.append((topic, message, qos, retain))


def __push_report_queue():
    for queued in __publish_queue_reports:
        __instance.publish(*queued)
    __publish_queue_reports.clear()


def __push_queue():
    for queued in __publish_queue:
        __instance.publish(*queued)
    __publish_queue.clear()
