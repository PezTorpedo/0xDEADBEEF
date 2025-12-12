import config
import device_sync

import mpack

from .store_app_config import store_app_config
from .verify_config import is_device_config_valid


class ValidationError(Exception):
    def __init__(self, message):  # pylint: disable=useless-super-delegation
        super().__init__(message)


async def handle_device_config(mqtt_conn):
    # First time publish bridge state to the cloud without backoff

    async for msg in mqtt_conn.subscribe(config.google_iot_config):
        try:
            device_config = mpack.loads(msg["payload"])
            if is_device_config_valid(device_config):
                print("Received device config")
                store_app_config(device_config)
                device_sync.received_config(True)
            else:
                raise ValidationError("Device config is not valid")

        except Exception as error:
            print(f"Error occurred in parsing the config : {type(error).__name__} : {error}")
            device_sync.received_config(False)
