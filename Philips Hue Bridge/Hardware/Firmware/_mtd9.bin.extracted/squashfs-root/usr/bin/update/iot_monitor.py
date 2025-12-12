# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

from component import ComponentEvent
from util.diagnostics import loggable
from util.mqtt_proxy import MqttError, MqttProxy


@loggable
class IotMonitor:
    def __init__(self, mqtt: MqttProxy, event_sink):
        self.__mqtt = mqtt
        self.__event_sink = event_sink
        self.__connected = False
        self.task = self.__mqtt_subscribe_loop()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        pass

    async def __mqtt_subscribe_loop(self):
        self._logger.info("Awaiting for IoT connectivity events")
        async for message in self.__mqtt.subscribe("$SYS/broker/connection/cloud/state"):
            try:
                connected = message["payload"] == b"1"
                self._logger.info("IoT connectivity event, connected=%s", connected)
                if not self.__connected and connected:
                    await self.__event_sink(
                        ComponentEvent(cid="any", command="connected", source="iot", version="unknown")
                    )
                    self.__connected = True
                    self.__mqtt.iot_connected(True)
            except MqttError:
                raise
            except Exception:
                self._logger.exception("Error in the MQTT subscribe loop")
