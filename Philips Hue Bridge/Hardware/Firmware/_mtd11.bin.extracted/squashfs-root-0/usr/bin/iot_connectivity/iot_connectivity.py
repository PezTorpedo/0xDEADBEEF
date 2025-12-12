#! /usr/bin/env micropython
import argparse
import asyncio
import gc

import diagnostics
import settings
from broker_configuration import handle_broker_config
from diagnostics.client import DiagnosticsClient
from diagnostics.connectivity_diagnostics import ConnectivityDiagnostics
from diagnostics.connectivity_stats import ConnectivityStats
from diagnostics.periodic_reports import periodic_reports_for_cloud, periodic_reports_local
from echo_message import echo_message_handler
from monitor_provisioning import process_provisioning_status
from mqtt_bridge_state import track_bridge_state
from reprovisioning import handle_reprovision_command, handle_reprovisioning

from hueutils.gather import gather_ex
from hueutils.queue import Queue
from mqttext import MqttExt


def _configure_garbage_collector():
    # run periodical garbage collection every half an hour, because by default we refresh jwt every hour
    async def periodical_gc_collect():
        while True:
            gc.collect()
            await asyncio.sleep(settings.jwt_refresh_period // 2)

    # setting the threshold triggers garbage collection whenever heap allocations reach the threshold value
    gc.threshold((gc.mem_alloc() + gc.mem_free()) // 2)
    asyncio.create_task(periodical_gc_collect())


async def main(args):
    _configure_garbage_collector()
    diagnostics_client = DiagnosticsClient()
    connectivity_stats = ConnectivityStats(diagnostics_client)
    conn_report_queue = Queue()
    reprovision_queue = Queue()
    disconnect_track_queue = Queue()

    try:
        tasks = []
        tasks.append(handle_reprovisioning(reprovision_queue))
        tasks.append(handle_broker_config())
        tasks.append(connectivity_stats.track_connectivity(conn_report_queue))
        tasks.append(periodic_reports_for_cloud(connectivity_stats))

        m = MqttExt(settings.daemon_name)
        m.will_set(f"status/{settings.daemon_name}/running", "0", 1, True)

        async with m as connection:
            # deprecating this flag on mqtt topic as this will not keep the status up to date
            connection.publish(f"status/{settings.daemon_name}/running", "1", retain=True)

            # the following tasks relate to the connection to the local broker, so they will be destroyed if
            # the connection drops
            mqtt_tasks = []

            # worker_task will throw on a disconnection
            mqtt_tasks.append(connection.worker_task)

            if args.send_log:
                print("sending mqtt logs enabled.")
                iot_diag = ConnectivityDiagnostics(connection, diagnostics_client)

                mqtt_tasks.append(iot_diag.send_mosquitto_logs())
            mqtt_tasks.append(
                track_bridge_state(connection, conn_report_queue, reprovision_queue, disconnect_track_queue)
            )
            mqtt_tasks.append(echo_message_handler(connection))
            mqtt_tasks.append(periodic_reports_local(connectivity_stats, connection))
            mqtt_tasks.append(process_provisioning_status(connection))
            mqtt_tasks.append(handle_reprovision_command(connection))

            diagnostics.events.send_event(diagnostics_client, "restart")

            await gather_ex(*tasks + mqtt_tasks)
    except BaseException as e:
        print(str(e))
        print("Unrecoverable error in main loop, quitting")
    finally:
        await asyncio.sleep(3)  # lets wait for sometime to close all pending tasks


print("starting {settings.daemon_name}...")
try:
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--send-logs", dest='send_log', action='store_true', help="Send mosquitto logs")
    arg_parser.add_argument("--no-send-logs", dest='send_log', action='store_false', help="Do not send mosquitto logs")
    args = arg_parser.parse_args()
    asyncio.run(main(args))
except KeyboardInterrupt:
    pass
print("exiting")
