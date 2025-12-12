# The response of the JWT request is received as per the following -
# - Topic - iot/in/app_name/jwt
# - Payload –
#     - Format - JSON, mpack
# ```
# {
# 'token': JWT token,
# 'refreshAfter': time after which the JWT should be renewed
# }
# ```

__cloud_connected = False
__subscribers = []


def is_cloud_connected():
    return __cloud_connected


def subscribe(callback):
    if callback not in __subscribers:
        __subscribers.append(callback)
        callback(__cloud_connected)


async def monitor_iot_connection(mqtt_conn):
    global __cloud_connected
    async for message in mqtt_conn.subscribe("$SYS/broker/connection/cloud/state"):
        try:
            __cloud_connected = message["payload"] == b"1"
            for subscriber in __subscribers:
                subscriber(__cloud_connected)
        except Exception:
            # self._logger.exception("Error in the MQTT subscribe loop")
            print("Error in the MQTT subscribe loop")
