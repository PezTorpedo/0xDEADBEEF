# Signify Company Confidential.
# Copyright (C) 2025 Signify Holding.
# All rights reserved.

import asyncio
import errno
import os
import time

import config

from hueutils.queue import Queue

# pylint: disable=too-many-arguments,unused-argument

# maps are used to reduce the size of the event log
states_map = {
    "backing_off": 1,
    "wait_for_iot_connection": 2,
    "wait_for_expired_token": 3,
    "requesting_token": 4,
    "keyerror": 5,
    "oserror": 6,
    "cancelled_error": 7,
    "state_unknown": -1,
}

events_map = {
    "backoff_expired": 1,
    "iot_connection": 2,
    "received": 3,
    "config_updated": 4,
    "timeout": 5,
    "token_requested": 6,
    "exception": 7,
}

apps_map = {
    "analytics": 1,
    "bridge_analytics": 2,
    "diagnostics": 3,
    "websockets": 4,
    "no_app": -1,
}


class EventLogger:
    """
    This class is responsible for logging events and data to a specified MQTT topic.

    Attributes:
        mqtt: An MQTT client instance used to publish the event log.
    """

    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):  # noqa: ARG002
        if cls._instance is None:
            cls._instance = super(EventLogger, cls).__new__(cls)
        return cls._instance

    def __init__(self, *args, **kwargs):  # noqa: ARG002
        if self.__class__._initialized:
            return
        self._log_queue = Queue()
        self.__class__._initialized = True

    def log_event(self, state_type, event_type, app_type, is_connected, desc):
        """
        Logs an event to the configured MQTT topic.

        Args:
            event_type (str): The type of event.
            state_type (str): The state type.
            app_type (str): The application type.
            is_connected (bool): Connection status.
            desc (str): additional details.
        """
        try:
            # [ ] and , are not suited for SQL queries
            desc = ''.join(ch for ch in desc if ch not in '[],')
            log_line = f"{time.time()}, {states_map[state_type]}, {events_map[event_type]}, {apps_map[app_type]}, {is_connected}, {desc}"
            self._log_queue.put(log_line)
        except Exception as exc:
            print(f"Error occurred in EventLogger: {type(exc).__name__} : {exc}")

    async def write_events_to_temp_file(self):
        curr_time = int(time.time())

        os.makedirs(config.event_log_dir, exist_ok=True)
        os.makedirs(config.temp_log_dir, exist_ok=True)
        index = 1

        while True:
            try:
                # The logs are first written to a file in a path such as
                # /tmp/temp_log/1. When the file has collected data for 1hr;
                # it's moved to /tmp/token_log/. We always keep last 6 files so
                # in worst case at max 1 hr of logs will not be available.
                # Radar daemon reads /tmp/token_log/ and adds it to the iot_connection
                # report
                temp_log_file = config.temp_log_dir + str(index)
                log_lines = []
                curr_time = int(time.time())
                tm = curr_time

                # we collect 1 hr of data
                while tm - curr_time < config.log_period:
                    line = await self._log_queue.get()
                    tm = int(time.time())
                    log_lines.append(line)

                with open(temp_log_file, "a", encoding="utf-8") as fp:
                    for line in log_lines:
                        fp.write(line + "\n")

                # to avoid the race condition where radar and croupierd access the same
                # file; the moving of file will ensure that it's available to radar
                # only after the move is complete.
                try:
                    os.rename(temp_log_file, f"{config.event_log_dir}{tm}")

                except OSError as err:
                    if err.errno != errno.ENOENT:
                        os.remove(temp_log_file)

                self._truncate_log_data(config.event_log_dir)
                await asyncio.sleep(2)

            except asyncio.CancelledError:
                print("Task cancelled")
                break

            except Exception as exc:
                print(f"Error occurred in writing data : {type(exc).__name__} : {exc}")

            index = index + 1

    def _truncate_log_data(self, log_dir):
        log_files = []
        try:
            log_files = os.listdir(log_dir)
        except OSError as e:
            print(f"Error occurred while listing log directory {log_dir}: {e}")
            return

        log_files.sort()
        # since the report is sent every 6hr so we keep 6 files
        while len(log_files) > 6:
            file_path = log_dir + log_files[0]

            try:
                os.remove(file_path)
                log_files.pop(0)

            except OSError as e:
                # if the file does not exist, we can ignore it
                if e.errno != errno.ENOENT:
                    print(f"Error occurred while deleting file {file_path}: {e}")
                else:
                    log_files.pop(0)
