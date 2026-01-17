# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

import heapq
from asyncio import CancelledError, Event
from asyncio import TimeoutError as AsyncioTimeoutError
from asyncio import wait_for
from time import ticks_add, ticks_diff, ticks_ms

from component import ComponentEvent
from util.diagnostics import loggable
from util.misc import plu, pretty_interval
from util.singleton import singleton


class __ScheduleItem:
    def __init__(self, event: ComponentEvent):
        self.event = event

    def __lt__(self, other: "__ScheduleItem") -> bool:
        return self.event.when < other.event.when


def after(seconds: float) -> int:
    """
    Returns the timestamp in millisecond-resolution ticks, corresponding
    to now + seconds in absolute time.
    """
    return ticks_add(ticks_ms(), int(seconds * 1000))


@singleton
@loggable
class Scheduler:
    """
    Scheduler allows to register an arbitrary number of events
    at some point in the future and sinks them when the time is due.
    """

    def __init__(self):
        self.__event_heap = []
        self.__event_heap_semaphore = Event()
        self.task = self.__scheduler_task()
        self.event_sink = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        pass

    async def __scheduler_task(self):
        self._logger.info("Started")
        try:
            while True:
                self.__event_heap_semaphore.clear()
                # Handle expired events.
                while self.__event_heap and ticks_diff(self.__event_heap[0].event.when, ticks_ms()) < 1000:
                    due_event: __ScheduleItem = heapq.heappop(self.__event_heap)
                    if self.__event_heap and due_event.event.obsoleted_by(self.__event_heap[0].event):
                        continue
                    await self.event_sink(due_event.event)  # pylint: disable=not-callable
                # Sleep until the next event is due, or until the event queue changes.
                if self.__event_heap:
                    next_event_due_in_s = ticks_diff(self.__event_heap[0].event.when, ticks_ms()) / 1000
                    if next_event_due_in_s > 0:
                        self._logger.debug(
                            "Sleeping for %s, %s in the queue",
                            pretty_interval(next_event_due_in_s),
                            plu(len(self.__event_heap), "event"),
                        )
                        try:
                            await wait_for(self.__event_heap_semaphore.wait(), next_event_due_in_s)
                        except AsyncioTimeoutError:
                            pass
                else:
                    self._logger.debug("Sleeping, no events in the queue")
                    await self.__event_heap_semaphore.wait()
        except CancelledError:
            self._logger.info("Interrupted")

    def schedule_event(self, event: ComponentEvent):
        """
        Schedules an event for execution at the given absolute time.
        The event must have at least `when` and `command` properties set.
        """
        event.complement(source="schedule", cid="any", version="unknown")
        report_in_s = ticks_diff(event.when, ticks_ms()) / 1000
        if report_in_s > 0:
            self._logger.info("Scheduling event in %s, command=%s", pretty_interval(report_in_s), event.command)
        else:
            self._logger.info("Scheduling event now, command=%s", event.command)
        heapq.heappush(self.__event_heap, __ScheduleItem(event))
        self.__event_heap_semaphore.set()
