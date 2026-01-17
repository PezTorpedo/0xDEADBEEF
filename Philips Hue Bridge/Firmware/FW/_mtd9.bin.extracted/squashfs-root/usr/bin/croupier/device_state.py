# pylint: disable=unspecified-encoding
import json
import time

import config
from utilities import bridge

import mpack

_SCHEMA_VERSION = 3


class DeviceStateHandler:
    """DeviceStateHandler is responsible for preparing payload for state message and
    publishing it on the remapped state topic.
    It publishes a JSON formatted state payload (compressed using mpack).
    The sample state message looks following:
    {
        "ts": 1622199146940,
        "schema": 3,
        "data": {
            "fflags": {
                "CONFIG_OPT": "true",
                "NEW_FFLAG": "another-string-value"
            },
            "device": {
                "sw": "9876543210",
                "type": "bsb002",
                "factory_reset_cnt": 1
            }
        }
    }
    To support more feature flags, modify supported_features.json
    """

    def __init__(self):
        self.__payload = None

    def _get_envelope(self):
        return {
            "schema": _SCHEMA_VERSION,
            "ts": int(time.time() * 1000),
        }

    def _get_data(self):
        return {
            # It is not required to check if the list of feature flags is empty
            # The cloud service is equipped to handle it. Moreover, sending of the state
            # should not be halted in the absence of feature flags because cloud sends
            # URLs of services on the basis of state message.
            "fflags": self._get_supported_features(),
            "device": {
                "type": bridge.device_type(),
                "sw": bridge.sw_version(),
                "factory_reset_cnt": bridge.factory_reset_count(),
            },
        }

    def _get_supported_features(self):
        try:
            with open(config.supported_features_file, "r") as fd:
                return json.loads(fd.read())

        except Exception as exc:
            print(f"Failed to load supported features list. error: {exc}")
            return {}

    def disable_config_optimization(self):
        self.__payload["data"]["fflags"]["CONFIG_OPT"] = False

    def prepare_payload(self):
        self.__payload = self._get_envelope()
        self.__payload["data"] = self._get_data()

    def publish_device_state(self, mqtt):
        if self.__payload:
            mqtt.publish(config.google_iot_state, mpack.dumps(self.__payload), retain=True)
        else:
            raise ValueError("payload is not initialized")


def send_state(mqtt_conn):
    try:
        print("Sending device state")
        device_state = DeviceStateHandler()
        device_state.prepare_payload()
        device_state.publish_device_state(mqtt_conn)

    except Exception as e:
        print("Error happened while sending state: ", e)
