import config
import token_sync
import tokens
from utilities.event_logger import EventLogger

import mpack

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


async def handle_tokens(mqtt_conn):
    app_name_index = config.jwt_subscription.split("/").index("+")
    evt_logger = EventLogger()
    async for msg in mqtt_conn.subscribe(config.jwt_subscription):
        try:
            segments = msg["topic"].decode().split("/")
            if len(segments) <= app_name_index:
                print("Topic without application name received")
                return

            app_name = segments[app_name_index]
            server_response = mpack.loads(msg["payload"])
            auth_validity = server_response["refreshAfter"]
            auth_token = server_response["token"]
            print(f"Updated {app_name} token with validity {auth_validity}")
            tokens.store(app_name, auth_token, auth_validity)
            token_sync.received_token()
            evt_logger.log_event("state_unknown", "received", app_name, True, "")

        except KeyError:
            evt_logger.log_event("keyerror", "exception", "no_app", True, "token_receive error")
