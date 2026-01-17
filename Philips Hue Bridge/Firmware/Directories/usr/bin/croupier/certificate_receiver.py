# Signify Company Confidential.
# Copyright (C) 2025 Signify Holding.
# All rights reserved.

import base64
import subprocess

import config

from hueutils.c_functions import fsync

key_data = "/tmp/key_data"


async def receive_certificate(mqtt_conn, exp_backoff, diagnostics):
    async for msg in mqtt_conn.subscribe(config.cert_receive_topic):
        diagnostics.send("certificate_received", config.data_id, "Received response from the cloud", 0)
        try:
            decoded_data = base64.b64decode(msg["payload"])
            with open(key_data, 'wb') as fp:
                fp.write(decoded_data)
                fsync(fp.fileno())

            # install the received certificate
            # pylint: disable=subprocess-run-check
            print("Installing Hue certificate")
            result = subprocess.run(['certificate_upgrade', 'install', key_data])
            diag_message = ""
            if result.returncode == 0:
                diag_message = "Succeeded"
                exp_backoff.reset()
            else:
                diag_message = "Failed"

            diagnostics.send(
                "certificate_installation",
                config.data_id,
                diag_message,
                result.returncode,
            )
            print(diag_message)

        except Exception as error:
            print(f"Error occurred in receive_certificate : {type(error).__name__} : {error}")
