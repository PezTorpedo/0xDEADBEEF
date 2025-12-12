#! /usr/bin/env micropython

import asyncio
import gc

import certificate_receiver
import certificate_request
import config
import device_config
import device_sync
import iot_monitor
import token_receiver
import token_sync
from diagnostics import Diagnostics
from utilities import bridge
from utilities.event_logger import EventLogger
from utilities.exponential_backoff import ExponentialBackOff
from utilities.token_dirs import prepare_token_dirs

from hueutils.gather import gather_ex
from mqtt import Mqtt
from mqtt.mosquitto import MqttError


async def main():
    # setting the threshold triggers garbage collection whenever heap allocations reach the threshold value
    gc.threshold((gc.mem_alloc() + gc.mem_free()) // 2)
    prepare_token_dirs()
    bridge.init_config()
    exp_backoff = ExponentialBackOff(config.vault_req_backoff_min, config.vault_req_backoff_max)
    while True:
        try:
            mqtt_conn = Mqtt(config.daemon_name)
            diagnostics = Diagnostics()

            async with mqtt_conn as connection:
                tasks = [
                    connection.worker_task,
                    EventLogger().write_events_to_temp_file(),
                    token_sync.handle_tokens(connection),
                    token_receiver.handle_tokens(connection),
                    device_config.handle_device_config(connection),
                    device_sync.handle_device_sync(connection),
                    iot_monitor.monitor_iot_connection(connection),
                    certificate_request.certificate_handler(connection, exp_backoff, diagnostics),
                    certificate_receiver.receive_certificate(connection, exp_backoff, diagnostics),
                ]

                print("Croupierd started")

                await gather_ex(*tasks)
        except (asyncio.CancelledError, MqttError):
            print("Connection closed")

        finally:
            await asyncio.sleep(config.wait_before_retry)


print("Starting...")
try:
    asyncio.run(main())
except KeyboardInterrupt:
    pass
except BaseException as exc:
    print(f"Error occurred {str(exc)}")
print("exiting")
