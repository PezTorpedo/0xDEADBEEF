import json

import settings
from loggingclient import InitialisationError, LoggingClient


class DiagnosticsClient:
    """
    Diagnostics class to send diagnostic messages to the Messenger via the LoggingClient.
    """

    def __init__(self, mqtt_host: str = settings.mqtt_host, mqtt_port: int = settings.mqtt_port):
        try:
            self._logging_client = LoggingClient(settings.daemon_name, mqtt_host, mqtt_port)
        except InitialisationError as e:
            print(f"Failed to initialize LoggingClient: {e}")
            self._logging_client = None

        self._total_messages = 0

    def send(self, body: dict, report_type: str, report_subtype: str = ""):
        """
        Send diagnostics message to the Messenger.

        :param body: The body of the diagnostics message.
        :param report_type: The type of the diagnostics report.

        :return: None
        """
        if self._logging_client is None:
            print("LoggingClient is not initialized, cannot send diagnostics message.")
            return

        self._total_messages += 1
        body["daemon_report_counter"] = self._total_messages

        try:
            self._logging_client.log(
                "diagnostics",
                report_type,
                report_subtype,
                json.dumps(body),
            )
        except Exception as e:
            print(f"Failed to send diagnostics message: {e}")
