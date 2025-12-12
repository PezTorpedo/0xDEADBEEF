# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

from time import time as now_s
from time import time_ns as now_ns

import config
from component import ComponentEvent
from observer_diagnostics import ObserverDiagnostics
from util.diagnostics import loggable
from util.misc import plu
from util.mqtt_proxy import MqttError, MqttProxy, mqtt_publish
from util.persistence import unpack

import mpack

__SCHEMA = 3


@loggable
class FrontendIot:
    def __init__(self, mqtt: MqttProxy, event_sink):
        self.__mqtt = mqtt
        self.__event_sink = event_sink
        self.__last_seen_sid = 0
        self.task = self.__mqtt_subscribe_loop()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        pass

    def __parse_otau_response(self, payload: dict):
        schema, sid = payload["schema"], payload.get("sid")
        if schema != __SCHEMA:
            self._logger.warning("Dropping IoT event due to unsupported schema, sid=%s, schema=%s", sid, schema)
            return
        if sid and int(sid) != 0 and int(sid) <= self.__last_seen_sid:
            self._logger.warning(
                "Dropping out-of-order IoT event, sid=%s, schema=%s, last_sid=%s", sid, schema, self.__last_seen_sid
            )
            return
        self.__last_seen_sid = int(sid)
        self._logger.info("IoT event with %s, sid=%s", plu(len(payload["data"]["comps"]), "component"), sid)

        ObserverDiagnostics().observe_componentlist_received(
            component_count=len(payload["data"]["comps"]), last_seen_sid=self.__last_seen_sid
        )

        for otau_component in payload["data"]["comps"]:
            cid, version, url, checksum, mandatory = unpack(
                keys=["cid", "ver", "url", "cs", "man"], from_dict=otau_component
            )
            cid = cid.lower()
            if cid.startswith(config.zigbee_component_prefix):
                mac = otau_component["mac"].lower()
                cid = f"{config.zigbee_component_prefix}{mac}"
            yield ComponentEvent(
                eid=now_ns(),
                command="update",
                cid=cid,
                source="iot",
                version=version,
                url=url,
                checksum=checksum,
                mandatory=mandatory,
            )

    async def __mqtt_subscribe_loop(self):
        self._logger.info("Awaiting for IoT component events")
        async for message in self.__mqtt.subscribe("iot/in/otau"):
            try:
                payload = mpack.loads(message["payload"])
                self._logger.debug("IoT event, payload=%s", payload)
                await self.__event_sink(self.__parse_otau_response(payload))
            except MqttError:
                raise
            except Exception as e:
                self._logger.exception("Error in the MQTT subscribe loop for IoT component events: %s", e)

    @staticmethod
    def report(components: list):
        report = {
            "ts": int(now_s()),
            "sid": int(now_ns()),
            "schema": __SCHEMA,
            "data": {
                "comps": components,
            },
        }
        # We don"t know if this has reached the destination, but that"s OK.
        # Eventually a daily report will be sent out.
        mqtt_publish("iot/out/otau", mpack.dumps(report), 1)
