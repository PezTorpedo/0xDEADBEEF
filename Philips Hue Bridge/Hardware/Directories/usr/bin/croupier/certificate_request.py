# Signify Company Confidential.
# Copyright (C) 2025 Signify Holding.
# All rights reserved.

import asyncio
import json
import subprocess
from asyncio import CancelledError

import config
import iot_monitor


class CertificateRequest:
    """
    This class is responsible for sending a certificate request to the vault.

    Attributes:
        client: An MQTT client instance used to publish the certificate request.

    Methods:
        send():
            Sends a certificate request message to the configured MQTT topic.
    """

    def __init__(self, mqtt_client, diagnostics):
        self.client = mqtt_client
        self.diagnostics = diagnostics

    def send(self):
        message = {"data_id": config.data_id}
        self.client.publish(config.cert_request_topic, json.dumps(message))
        print("Certificate request sent")

        self.diagnostics.send(
            "certificate_requested",
            config.data_id,
            "Certificate Request sent",
            0,
        )


async def certificate_handler(mqtt_conn, exp_backoff, diagnostics):
    request_sender = CertificateRequest(mqtt_conn, diagnostics)

    while not _check_if_cert_installed():
        try:
            if iot_monitor.is_cloud_connected():
                request_sender.send()

            await asyncio.sleep(exp_backoff.get_next_delay())

        except CancelledError:
            break

        except Exception as exc:
            print(f"Error occurred in certificate_handler : {type(exc).__name__} : {exc}")


def _check_if_cert_installed():
    try:
        result = subprocess.run(['certificate_upgrade', 'check'])  # pylint: disable=subprocess-run-check
        print(result.stdout)
        return result.returncode == 0

    except OSError as error:
        print(f"Error occurred in check_if_cert_installed : {type(error).__name__} : {error}")
    return False
