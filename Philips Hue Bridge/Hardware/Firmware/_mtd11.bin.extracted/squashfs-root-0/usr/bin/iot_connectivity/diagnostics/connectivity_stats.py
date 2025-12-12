import asyncio
import time

import settings
import shared

from . import events
from .stats_counter import StatsCounter

_total_messages = 0


class ConnectivityStats:
    def __init__(self, diagnostics):
        self._diagnostics = diagnostics

        self._disconnected = StatsCounter(settings.report_period_8hr)
        self._connected = StatsCounter(settings.report_period_8hr)
        self._currently_connected = None
        self._last_transition = 0
        self._daily_connection_count = 0
        self._daily_max_connection_duration = 0

    async def track_connectivity(self, queue):
        # track_bridge_state will always fire an initial message into the queue
        while True:
            try:
                when, new_connection_state = await queue.get()
            except asyncio.CancelledError:
                break

            delta = time.ticks_diff(when, self._last_transition) / 1000

            if self._currently_connected is True:
                self._connected.add(delta)
                self._update_daily_stats(delta)
            elif self._currently_connected is False:
                self._disconnected.add(delta)

            event_name = "connected" if new_connection_state else "disconnected"
            event_description = "" if new_connection_state else shared.last_disconnect_error
            events.send_event(self._diagnostics, event_name, event_description)

            self._last_transition = when
            self._currently_connected = new_connection_state

    def _close_report_period(self):
        now = time.ticks_ms()

        delta = time.ticks_diff(now, self._last_transition) / 1000
        if self._currently_connected is True:
            self._connected.add(delta)
        elif self._currently_connected is False:
            self._disconnected.add(delta)

        self._last_transition = now

    def send_report(self):
        global _total_messages

        _total_messages += 1

        # as counters only get updated on transitions, we need to do something to capture current state
        self._close_report_period()

        body = {
            "report_counter": _total_messages,
            "connected": self._connected.get(),
            "disconnected": self._disconnected.get(),
        }

        self._connected.clear()
        self._disconnected.clear()

        self._diagnostics.send(body, "iot_connectivity_stats")

    def _update_daily_stats(self, duration):
        self._daily_max_connection_duration = max(duration, self._daily_max_connection_duration)
        self._daily_connection_count = self._daily_connection_count + 1

    def reset_daily_stats(self):
        self._daily_max_connection_duration = 0
        self._daily_connection_count = 0

    def get_daily_stats(self):
        return self._daily_connection_count, self._daily_max_connection_duration
