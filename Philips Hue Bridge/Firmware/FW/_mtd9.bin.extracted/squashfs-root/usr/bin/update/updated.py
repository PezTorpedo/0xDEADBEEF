#! /usr/bin/env micropython

# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

import argparse
import asyncio
import gc
import json
from time import time as now_s

import config
import util.diagnostics as diag
from bridge import hal, uboot
from bridge.bootslot import Bootslot
from component import ComponentEvent
from frontend_iot import FrontendIot
from frontend_mqtt import FrontendMqtt
from frontend_sideload import FrontendSideload
from frontend_zigbee import FrontendZigbee
from iot_monitor import IotMonitor
from reactor import Reactor
from scheduler import Scheduler
from util.calculate_report import calculate_report_period_offset
from util.misc import simple_write
from util.mqtt_proxy import MqttProxy
from zigbee_fw_fetcher import ZigbeeFwFetcher

from hueutils.gather import gather_ex

_log = diag.get_logger(__name__)


def _configure_garbage_collector():
    async def joe_the_janitor():
        while True:
            gc.collect()
            await asyncio.sleep(1)

    gc.threshold(config.gc_threshold)
    asyncio.create_task(joe_the_janitor())


def _configure_oom_killer():
    _log.info("Setting OOM score adjustment to %d (in `%s`)", config.oom_adj_value, config.oom_adj_path)
    try:
        simple_write(config.oom_adj_path, str(config.oom_adj_value))
    except Exception:
        _log.exception("Failed to set OOM scorfe adjustment")


def _configure_bridge_component_override():
    override = uboot.read_variable(config.bridge_component_override)
    if override:
        _log.info('Bridge component override %s -> %s', config.bridge_component, override)
        config.bridge_component = override


async def _register_bridge_component(event_sink):
    await event_sink(
        ComponentEvent(command='sync', cid=config.bridge_component, source='unknown', version=Bootslot().active_version)
    )


def _schedule_initial_zigbee_poll(force_clip_update=False):
    Scheduler().schedule_event(
        ComponentEvent(
            command='zdb_change_trigger', update_counter=0, when=now_s() + 5, force_clip_update=force_clip_update
        )
    )


def _start_ticks():
    Scheduler().schedule_event(ComponentEvent(command='tick', when=now_s() + 120))


def _last_will(mqtt: MqttProxy):
    mqtt.will_set('updated/bridge_update_state', json.dumps({'bridge': 'noupdates', 'devices': {}}), retain=True)


def _mqtt_connect_callback(connect_count: int):
    # Avoid posting events on the first ever connect, before everything is initialised.
    if connect_count > 1:
        # Update the zigbee node list and the CLIP status to avoid
        # getting stuck in case the broker disappeared at the most
        # unfortunate moment.
        _schedule_initial_zigbee_poll(True)


async def main():
    _configure_garbage_collector()
    _configure_oom_killer()
    try:
        async with MqttProxy(
            clientid='updated',
            hostname=config.fixed["mqtt_host"],
            port=int(config.fixed["mqtt_port"]),
            postinitcall=_last_will,
            connect_callback=_mqtt_connect_callback,
        ) as mqtt_proxy:
            _configure_bridge_component_override()
            await hal().startup()
            _ = Bootslot()
            _ = ZigbeeFwFetcher()
            scheduler = Scheduler()
            async with Reactor() as reactor:
                scheduler.event_sink = reactor.on_event
                async with FrontendIot(mqtt_proxy, reactor.on_event) as frontend_iot:
                    async with FrontendMqtt(mqtt_proxy, reactor.on_event) as frontend_mqtt:
                        async with FrontendZigbee(mqtt_proxy, reactor.on_event) as frontend_zigbee:
                            async with IotMonitor(mqtt_proxy, reactor.on_event) as iot_monitor:
                                await _register_bridge_component(reactor.on_event)
                                _schedule_initial_zigbee_poll()
                                _start_ticks()
                                async with FrontendSideload(mqtt_proxy, reactor.on_event) as frontend_sideload:
                                    tasks = []
                                    tasks.append(scheduler.task)
                                    tasks.append(mqtt_proxy.worker_task)
                                    tasks.append(iot_monitor.task)
                                    tasks.append(frontend_iot.task)
                                    tasks.append(frontend_mqtt.task)
                                    tasks.append(frontend_zigbee.task)
                                    tasks.append(frontend_sideload.task)
                                    task_results = await gather_ex(*tasks, return_exceptions=True)
                                    _log.warning('Task results: %s', task_results)
    except (asyncio.CancelledError, KeyboardInterrupt):
        _log.info('Main loop interrupted')
    except Exception:
        _log.exception('Unrecoverable error in the main loop')


try:
    p = argparse.ArgumentParser()
    p.add_argument('--host', help='Mqtt broker', default=config.fixed["mqtt_host"])
    p.add_argument('--port', help='Mqtt broker port', default=config.fixed["mqtt_port"])
    p.add_argument('--kernel_cmdfile', help='Force the kernel arguments file', default=config.fixed["kernel_cmdline"])
    p.add_argument('--platform', help='Force a specific HAL', default=config.fixed["platform"])
    p.add_argument('--use_syslog', help='Use syslog for logging instead of stdout', action='store_true', default=False)
    p.add_argument(
        '--verbose', help='Include debug and trace messages in logging output', action='store_true', default=False
    )
    args = p.parse_args()

    # Make sure this is set before the first call to `hal()` to prevent
    # it from loading the default HAL and memoizing it.
    config.fixed["platform"] = args.platform

    config.fixed['verbose'] = bool(args.verbose)
    config.fixed['report_period_offset'] = calculate_report_period_offset(hal().get_board_id())
    config.fixed["kernel_cmdline"] = args.kernel_cmdfile
    config.fixed["mqtt_host"] = args.host
    config.fixed["mqtt_port"] = args.port

    diag.initialise_logger(use_syslog=args.use_syslog, verbose=args.verbose)

    _log.info('Starting...')
    asyncio.run(main())
except KeyboardInterrupt:
    _log.info('User interruption while starting.')
finally:
    _log.info('Exiting')
