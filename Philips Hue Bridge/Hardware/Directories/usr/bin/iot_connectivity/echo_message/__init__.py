import asyncio
import json
import time


# The following code (and related portions) can be removed as soon as
#   the Mosquitto bridge is deemed acceptable
async def echo_message_handler(mqtt):
    async for msg in mqtt.subscribe("iot/in/echo-cloud2bridge"):
        try:
            echo_msg = json.loads(msg["payload"].decode())

            # message contains times in ms
            await asyncio.sleep(echo_msg["ohceTimestamp"] / 1000 - time.time())

            reply_qos = 0

            if "qos" in echo_msg and echo_msg["qos"] == '1':
                reply_qos = 1

            echo_msg["infoDevice"] = "device2cloud - OK: Looking good"
            echo_msg["timestampDevice"] = int(time.time() * 1000)

            mqtt.publish("iot/out/echo-bridge2cloud", json.dumps(echo_msg), reply_qos)
        except (ValueError, KeyError):
            pass
