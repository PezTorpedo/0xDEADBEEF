# Signify Company Confidential.
# Copyright (C) 2025 Signify Holding.
# All rights reserved.

import config
from loggingclient import LoggingClient
from util.singleton import singleton


@singleton
class DiagnosticsProxy:
    _diag_client = None

    def __init__(self):
        self._diag_client = LoggingClient(
            config.daemon_name, config.fixed["mqtt_host"], int(config.fixed["mqtt_port"])
        )  # MQTT host and port just used for component tests

    def log(self, type_: str, body: str):
        self._diag_client.log("diagnostics", type_, "", body)
