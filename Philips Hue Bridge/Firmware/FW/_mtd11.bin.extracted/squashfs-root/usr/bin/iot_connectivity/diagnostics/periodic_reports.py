import asyncio
import json

import settings
import shared


async def periodic_reports_for_cloud(stats):
    while True:
        try:
            stats.send_report()
            await asyncio.sleep(settings.report_period_8hr)

        except asyncio.CancelledError:
            break


async def periodic_reports_local(stats, conn):
    while True:
        try:
            report = _format_body(stats)
            conn.publish(settings.topic_daily_conn_data, json.dumps(report), 0, True)

            stats.reset_daily_stats()
            await asyncio.sleep(settings.report_period_24hr)

        except asyncio.CancelledError:
            break


def _format_body(stats):
    conn_count, duration = stats.get_daily_stats()

    body = {
        "mqtt_connection_count": conn_count,
        "mqtt_max_connection_duration": duration,
        "iot_config_error": shared.last_config_error,
        "last_mqtt_connection_error": shared.last_disconnect_error,
    }

    return body
