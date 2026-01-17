import json

import config
from loggingclient import InitialisationError, LoggingClient


def _make_diagnostic_message(event_name: str, data_id: str, result: str, error_code: int) -> dict:
    return {
        "event": event_name,
        "data_id": data_id,
        "result": result,
        "error_code": error_code,
    }


class Diagnostics:
    """
    Diagnostics class to send diagnostic messages to the Messenger via the LoggingClient.
    """

    def __init__(self, mqtt_host: str = config.mqtt_host, mqtt_port: int = config.mqtt_port):
        try:
            self._logging_client = LoggingClient(config.daemon_name, mqtt_host, mqtt_port)
        except InitialisationError as e:
            print(f"Failed to initialize LoggingClient: {e}")
            self._logging_client = None

    def send(self, event_name: str, data_id: str, result: str, error_code: int):
        """
        Send diagnostics message to the Messenger.

        :param event_name: Name of the event that occurred.
        :param data_id: Identifier for the data related to the event.
        :param result: Result of the event.
        :param error_code: Error code of the event.
        :return: None
        """
        if self._logging_client is None:
            print("LoggingClient is not initialized, cannot send diagnostics message.")
            return

        try:
            self._logging_client.log(
                "diagnostics",
                "certificate_upgrade_log",
                "",
                json.dumps(_make_diagnostic_message(event_name, data_id, result, error_code)),
            )
        except Exception as e:
            print(f"Failed to send diagnostics message: {e}")
