import settings
import shared


class ConnectivityDiagnostics:
    def __init__(self, mqtt, diagnostics):
        self._mqtt = mqtt
        self._diagnostics = diagnostics

    async def send_mosquitto_logs(self):
        async for msg in self._mqtt.subscribe(settings.mqtt_log_subscription):
            log_line = msg["payload"].decode()

            # The disconnect error will be sent along with disconnect event.
            if settings.tag_disconnect_err in log_line and "cloud-iot" in log_line:
                shared.last_disconnect_error = log_line.replace(settings.tag_disconnect_err, "").strip()
            else:
                trimmed_log = ""
                if settings.tag_bridge_fail_err in log_line:
                    trimmed_log = log_line.replace(settings.tag_bridge_fail_err, "")
                elif settings.tag_connect_ack_err in log_line:
                    trimmed_log = log_line.replace(settings.tag_connect_ack_err, "")
                if trimmed_log:
                    self._diagnostics.send({"log": trimmed_log.strip()}, "mqtt_logs")
