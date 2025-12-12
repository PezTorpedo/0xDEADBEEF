import asyncio
import json
import os

import settings


async def handle_reprovisioning(queue):
    conn_state = None  # track_bridge_state will always fire an initial message into the queue

    while True:
        try:
            # state transitions are received in the queue. Give it up to failure_before_reprovision_period to change
            _, conn_state = await asyncio.wait_for(queue.get(), _read_retry_timeout())

        except asyncio.TimeoutError:
            # no transition was received in the maximum period

            # if it's connected, everyone is happy and there is nothing to do
            if conn_state:
                continue

            # otherwise, it means we've been disconnected for a while. Try reprovisioning
            os.system(f"force_reprovision {settings.provisioning_directory} {settings.no_iot_connection}")  # nosec
            print("Reprovisioning was forced  in the absence of IoT connection")

        except asyncio.CancelledError:
            break

        except Exception as exc:
            print(f"handle_reprovisioning: Exception caught! {exc}")


async def handle_reprovision_command(mqtt_conn):
    async for _ in mqtt_conn.subscribe(settings.reprovision_cmd):
        try:
            print("The bridge received reprovision command")
            os.system(f"force_reprovision {settings.provisioning_directory} {settings.reprovisioning_cmd}")  # nosec

        except asyncio.CancelledError:
            break

        except Exception as exc:
            print(f"handle_reprovision_command: Exception caught! {exc}")


def _read_retry_timeout():
    # The default value is to be used if service.json isn't available or
    # not a valid number
    retry_period = settings.default_force_reprovisioning_after
    try:
        with open(f"{settings.provisioning_directory}/service.json", "r") as f:  # pylint: disable=unspecified-encoding
            service_json = json.loads(f.read())
            retry_period = int(service_json["retry-timeout"])
    except Exception as exc:
        print(f"_read_retry_timeout: Exception caught! {exc}")
    print(f"The wait before provisioning period is {retry_period}s")
    return retry_period
