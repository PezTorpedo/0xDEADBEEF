# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

import json

from component import ComponentEvent
from util.diagnostics import loggable
from util.mqtt_proxy import MqttError, MqttProxy, mqtt_publish


@loggable
class FrontendZigbee:
    def __init__(self, mqtt: MqttProxy, event_sink):
        self.__mqtt = mqtt
        self.__event_sink = event_sink
        self.task = self.__mqtt_subscribe_loop()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        pass

    @staticmethod
    def request_node_list(update_counter=None):
        request = {
            "request_id": "whatever",
            "response_topic": "rpc/response/zigbeenodes_get",
            "body": {"update_counter": update_counter or 0},
        }
        mqtt_publish("rpc/request/zigbeenodes_get", json.dumps(request))

    @staticmethod
    def request_transfer_image(request_id: str, mac: str, path: str, version: int, block_request_delay=0):
        request = {
            "request_id": request_id,
            "response_topic": "rpc/response/smartlink_ota_transferimage",
            "body": {
                "mac": mac,
                "filename": path,
                "version": version,
                "blockrequestdelay": block_request_delay,
            },
        }
        mqtt_publish("rpc/request/smartlink_ota_transferimage", json.dumps(request))

    @staticmethod
    def request_ota_attributes(request_id: str, mac: str):
        request = {
            "request_id": request_id,
            "response_topic": "rpc/response/request_ota_attributes",
            "body": {"nodes": [mac]},
        }
        mqtt_publish("rpc/request/request_ota_attributes", json.dumps(request))

    @staticmethod
    def request_unicast_update(request_id: str, mac: str):
        request = {
            "request_id": request_id,
            "response_topic": "rpc/response/smartlink_ota_executeupdate",
            "body": {
                "mac": mac,
                "waittime": 0,
            },
        }
        mqtt_publish("rpc/request/smartlink_ota_executeupdate", json.dumps(request))

    @staticmethod
    def request_group_update(request_id: str, wait_time: int):
        request = {
            "request_id": request_id,
            "response_topic": "rpc/response/smartlink_ota_executeupdate",
            "body": {
                "waittime": wait_time,
            },
        }
        mqtt_publish("rpc/request/smartlink_ota_executeupdate", json.dumps(request))

    @staticmethod
    def request_sense_awake(macs: set):
        request = {
            "request_id": "whatever",
            "response_topic": "rpc/response/sense_awake",
            "body": {"nodes": list(macs)},
        }
        mqtt_publish("rpc/request/sense_awake", json.dumps(request))

    async def __mqtt_subscribe_loop(self):
        self._logger.info("Awaiting for Zigbee component events")
        async for message in self.__mqtt.subscribe("rpc/response/#"):
            try:
                topic = message["topic"].decode()
                payload = json.loads(message["payload"])
                self._logger.debug("Zigbee component event, topic=%s, request_id=%s", topic, payload["request_id"])
                command = None
                if topic == "rpc/response/zigbeenodes_get":
                    await self.__event_sink(
                        ComponentEvent(
                            cid="any",
                            command="sync",
                            source="ipbridge",
                            version="unknown",
                            nodes=payload["nodes"],
                            update_counter=payload["update_counter"],
                        )
                    )
                elif topic == "rpc/response/smartlink_ota_transferimage":
                    command = "transfer_ack"
                elif topic == "rpc/response/smartlink_ota_executeupdate":
                    command = "install_ack"
                else:
                    self._logger.warning("Unknown response topic %s", topic)
                if command:
                    await self.__event_sink(
                        ComponentEvent(
                            cid=payload["request_id"],
                            command=command,
                            source="ipbridge",
                            version="unknown",
                            result=payload["result"],
                            cause=payload["cause"],
                        )
                    )
            except MqttError:
                raise
            except Exception:
                self._logger.exception("Error in the MQTT subscribe loop")
