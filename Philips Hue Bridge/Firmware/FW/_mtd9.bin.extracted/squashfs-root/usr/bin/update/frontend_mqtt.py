# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

import json
from time import time as now_s

import config
from component import ComponentEvent
from util.diagnostics import loggable
from util.mqtt_proxy import mqtt_publish

from mqttext import MqttError, MqttExt


@loggable
class FrontendMqtt:
    def __init__(self, mqtt: MqttExt, event_sink):
        self.__mqtt = mqtt
        self.__event_sink = event_sink
        self.task = self.__mqtt_subscribe_loop()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        pass

    @staticmethod
    def publish_clip_update_state(clip_state: dict):
        mqtt_publish("updated/bridge_update_state", json.dumps(clip_state), retain=True)

    def __handle_execute(self, payload: bytes):
        # According to documentation trigger_source = [unknown, sideload, manual, autoupdate]
        trigger_source = payload.decode()
        self._logger.info("Install updates, trigger_source=%s", trigger_source)
        # This event will get dispatched to the bridge component only.
        yield ComponentEvent(
            command="install",
            cid=config.bridge_component,
            source="clip",
            version="unknown",
            flavour="normal",
            trigger_source=trigger_source,
        )
        # This event will get dispatched to the ComponentManager,
        # so it can deal with (multiple) Zigbee device updates.
        yield ComponentEvent(
            command="install",
            cid="any",
            source="clip",
            version="unknown",
            flavour="normal",
            trigger_source=trigger_source,
        )

    def __handle_check_for_update(self, _: bytes):
        self._logger.info("Check for updates")
        yield ComponentEvent(command="report", cid="any", source="clip", version="unknown", kind="manual")

    def __handle_zigbeenodes_changed(self, payload: bytes):
        body = json.loads(payload.decode())
        self._logger.debug("Zigbee datastore change, update_counter=%d", body["update_counter"])
        # Rate-limited event. In case of queuing only the event with
        # the greatest `update_counter` is preserved per uniqie `pid`.
        yield ComponentEvent(
            command="zdb_change_trigger",
            cid="any",
            source="ipbridge",
            version="unknown",
            update_counter=body["update_counter"],
            pid=body["pid"],
            flood_control=("pid", "update_counter"),
        )

    def __handle_zigbeenodes_deleted(self, payload: bytes):
        body = json.loads(payload.decode())
        self._logger.debug('Zigbee datastore change, delete nodes:%s', body['nodes'])
        yield ComponentEvent(
            command="zdb_delete_trigger", cid="any", source="ipbridge", version="unknown", nodes=body["nodes"]
        )

    def __handle_awake(self, payload: bytes):
        body = json.loads(payload.decode())
        timestamp = body["timestamp"]
        if now_s() - timestamp <= 7:
            cid = f"{config.zigbee_component_prefix}{body['mac'].lower()}"
            # Rate-limited event. In case of queuing only the event with
            # the greatest `awake_timestamp` is preserved per uniqie `cid`.
            yield ComponentEvent(
                command="sense_awake",
                cid=cid,
                source="ipbridge",
                version="unknown",
                awake_timestamp=timestamp,
                flood_control=("cid", "awake_timestamp"),
            )

    def __handle_test_override_parameter(self, payload: bytes):
        body = json.loads(payload.decode())
        self._logger.info("Test command: override parameter, body=%s", body)
        yield ComponentEvent(
            command="test_override_parameter", cid="any", source="test", version="unknown", overrides=body
        )

    def __handle_test_force_expire_state(self, payload: bytes):
        body = json.loads(payload.decode())
        self._logger.info("Test command: reset component, body=%s", body)
        mac = body['mac'].replace(':', '').lower()
        cid = f"{config.zigbee_component_prefix}{mac}"
        yield ComponentEvent(
            command="test_force_expire_state",
            cid=cid,
            source="test",
            version="unknown",
            expected_state=body["expected_state"],
        )

    async def __mqtt_subscribe_loop(self):
        self._logger.info("Awaiting for MQTT events")
        dispatch_table = {
            "updated/execute": self.__handle_execute,
            "updated/check_for_update": self.__handle_check_for_update,
            "updated/zigbeenodes_changed": self.__handle_zigbeenodes_changed,
            "updated/zigbeenodes_deleted": self.__handle_zigbeenodes_deleted,
            "updated/awake": self.__handle_awake,
            "updated/test/override_parameter": self.__handle_test_override_parameter,
            "updated/test/force_expire_state": self.__handle_test_force_expire_state,
        }
        async for message in self.__mqtt.subscribe("updated/#"):
            try:
                topic = message["topic"].decode()
                payload = message["payload"]
                if topic in dispatch_table:
                    await self.__event_sink(dispatch_table[topic](payload))
                elif topic != "updated/bridge_update_state":
                    self._logger.warning("Unknown MQTT command, topic=%s", topic)
            except MqttError:
                raise
            except Exception:
                self._logger.exception("Error in the MQTT subscribe loop")
