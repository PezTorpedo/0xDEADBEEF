# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

import json

from util.diagnostics import loggable
from util.mqtt_proxy import mqtt_publish


@loggable
class FrontendIpbridge:
    @classmethod
    def enable_interfaces(cls, test: bool, commissioning: bool, factory: bool):
        cls._logger.info(
            "Enabling interfaces: %s",
            ", ".join(
                [i[1] for i in zip((test, commissioning, factory), ("test", "commissioning", "factory")) if i[0]]
            ),
        )
        request = {
            "request_id": "whatever",
            "response_topic": "rpc/response/enable_test_interface",
            "body": {
                "allow_test_interface": test,
                "allow_commissioning_interface": commissioning,
                "allow_factory_interface": factory,
            },
        }
        mqtt_publish("rpc/request/enable_test_interface", json.dumps(request))
