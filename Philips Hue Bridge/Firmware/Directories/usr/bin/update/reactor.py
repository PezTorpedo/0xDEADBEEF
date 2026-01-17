# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

import heapq
from asyncio import Event, Task, create_task, sleep_ms

import config
from component import Component, ComponentEvent
from frontend_mqtt import FrontendMqtt
from reactor_component_helper import ComponentHelper
from reactor_report_helper import ReportHelper
from reactor_zigbee_helper import ZigbeeHelper
from util.diagnostics import loggable
from util.misc import wait_ex


@loggable
class Reactor:
    """
    Responsible for maintaining the list of registered components
    and for dispatching events to them.
    """

    def __init__(self):
        self.__fast_queue = []
        self.__event_heap = []
        self.__event_heap_semaphore = Event()
        self.__current_action: tuple = None
        self.__components = ComponentHelper()
        self.__report_helper = ReportHelper(self.__components)
        self.__zigbee_helper = ZigbeeHelper(self.__components)
        self.__last_clip_state = {}
        self.__event_handlers = {
            "test_override_parameter": ("self", self.__handle_test_override_parameter),
            "connected": ("report helper", self.__report_helper.handle_iot_connected),
            "report": ("report helper", self.__report_helper.handle_component_report),
            "install": ("zigbee helper", self.__zigbee_helper.handle_install),
            "zdb_change_trigger": ("zigbee helper", self.__zigbee_helper.handle_zdb_change_trigger),
            "zdb_delete_trigger": ("zigbee helper", self.__zigbee_helper.handle_zdb_delete_trigger),
            "sync": ("zigbee helper", self.__zigbee_helper.handle_sync),
            "tick": ("zigbee helper", self.__zigbee_helper.handle_tick),
        }

    async def __aenter__(self):
        self.__task: Task = create_task(self.__main_loop())
        return self

    async def __aexit__(self, *_):
        self.__task.cancel()
        await self.__task

    def __handle_test_override_parameter(self, event: ComponentEvent):
        for key, value in event.overrides.items():
            if key in config.dynamic:
                old_value = config.dynamic[key]
                old_type = type(old_value)
                new_type = type(value)
                if old_type is new_type:
                    self._logger.info("Overriding parameter, key=%s, value=%s, old_value=%s", key, value, old_value)
                    config.dynamic[key] = value
                else:
                    self._logger.error(
                        "Can't override parameter, key=%s, value=%s(%s), old_value=%s(%s)",
                        key,
                        new_type.__name__,
                        value,
                        old_type.__name__,
                        old_value,
                    )
            else:
                self._logger.error("Can't override unknown parameter, key=%s, value=%s", key, value)
        event.accept()

    async def __component_task_wrapper(self, task, event: ComponentEvent):
        """
        Runs the given task for the given event and notifies
        the main loop once the task is done.
        """
        try:
            await task(event)
        finally:
            self.__current_action = None
            event.accept()
            self.__event_heap_semaphore.set()

    async def __execute_event(self, component: Component, event: ComponentEvent) -> tuple:
        if event.asynchronous():
            return event, create_task(self.__component_task_wrapper(component.dispatch, event))
        try:
            await component.dispatch(event)
        except Exception:
            self._logger.exception(
                "Exception when dispatching event, cid=%s, extra=%s", event.cid, event.pick("command", "source")
            )
        event.accept()
        return None

    async def __dispatch_event(self, event: ComponentEvent) -> tuple:
        """Dispatches events to self, or to components."""
        # Pass over the last IoT report sequence in case recepient is interested.
        event.update(next_report_sequence=self.__report_helper.sequence + 1)
        if event.cid == "any":
            # Handle system events.
            if event.command in self.__event_handlers:
                destination, handler = self.__event_handlers[event.command]
                self._logger.debug("Dispatching event to %s, extra=%s", destination, event.pick("command", "source"))
                try:
                    return handler(event)
                except Exception:
                    self._logger.exception(
                        "Exception when dispatching event to %s, extra=%s", destination, event.pick("command", "source")
                    )
                    event.accept(error="exception")
                    return None
        else:
            # Handle component events.
            component = self.__components.find_or_instantiate(from_event=event)
            if component:
                self._logger.debug(
                    "Dispatching event to %s, extra=%s", event.cid, event.pick("command", "source", "version")
                )
                return await self.__execute_event(component, event)
        self._logger.warning("Can't dispatch event, fields=%s", event.pick("cid", "command", "source", "version"))
        event.accept(error="unhandled")
        return None

    async def __stop_current_action_if_outweighed(self, event: ComponentEvent):
        """
        Weighs the event at the top of the event heap against the currently
        performed action (if any) and stops the action if needed.
        """
        if self.__current_action:
            action, task = self.__current_action
            # A higher priority event should stop and replace a lower priority event.
            stop = event < action
            # With the following caveats.
            if action.command == "install" and action.cid == config.bridge_component:
                # Bridge install command can't be interrupted at all.
                stop = False
            elif action.command == "fetch" and event.command == "install" and event.cid == "any":
                # CLIP install trigger must stop Zigbee firmware fetch.
                stop = True
            elif (
                event.command == "install"
                and action.cid == config.bridge_component
                and event.cid == config.bridge_component
            ):
                # Bridge install commands always wait for bridge update commands to finish.
                stop = False
            elif not event.asynchronous():
                # The interrupting event must be asynchronous.
                stop = False
            if stop:
                self._logger.info(
                    "Event %s %s %s outweighs %s %s %s, stopping",
                    event.source,
                    event.command,
                    event.cid,
                    action.source,
                    action.command,
                    action.cid,
                )
                if not task.done():
                    task.cancel()
                    # It appears that very rarely CancelledError is not being raised
                    # in the task. So we hit it with the hammer on the head the second time
                    # in order to get the message through.
                    await sleep_ms(100)
                    task.cancel()
                    await task
                self.__current_action = None
            else:
                self._logger.debug(
                    "Event %s %s %s will be handled after %s %s %s is done",
                    event.source,
                    event.command,
                    event.cid,
                    action.source,
                    action.command,
                    action.cid,
                )

    def __postprocess_event_heap(self):
        """Cleans up the event queie from events that are for sure not relevant."""
        action, _ = self.__current_action
        for event in self.__event_heap:
            if (
                event.command == "update"
                and event.source == "sideload"
                and event.cid == config.bridge_component
                and action.command == "install"
                and action.cid == config.bridge_component
            ):
                # Special case: the install handler for the bridge component is running
                # and a sideload has come in. As the install handler blocks forever,
                # the incoming sideload connection will remain open until the reboot.
                # This may cause issues, so we accept the event, causing the sideload
                # frontend to close the connection.
                self._logger.warning(
                    "Rejecting %s %s %s to %s because another action is in progress",
                    event.source,
                    event.command,
                    event.cid,
                    event.version,
                )
                event.accept(error="higher priority action in progress")
                break

    def __emit_clip_update_state(self, force_clip_update: bool):
        clip_update_state = self.__components.compute_clip_update_state()
        if force_clip_update or clip_update_state != self.__last_clip_state:
            self._logger.info(
                "CLIP update state changed, force=%s, bridge=%s, devices=%d",
                force_clip_update,
                clip_update_state["bridge"],
                len(clip_update_state["devices"]),
            )
            FrontendMqtt.publish_clip_update_state(clip_update_state)
            self.__last_clip_state = clip_update_state

    async def __main_loop(self):
        force_clip_update = False
        skip_count = 0
        while True:
            self.__event_heap_semaphore.clear()
            # Transfer events from the fast queue into the heap.
            while self.__fast_queue:
                heapq.heappush(self.__event_heap, self.__fast_queue.pop())
            if self.__event_heap:
                await self.__stop_current_action_if_outweighed(self.__event_heap[0])
                while self.__current_action is None and self.__event_heap:
                    force_clip_update |= self.__event_heap[0].get("force_clip_update", False)
                    self.__current_action = await self.__dispatch_event(heapq.heappop(self.__event_heap))
                if self.__current_action is not None and self.__event_heap:
                    self.__postprocess_event_heap()
            # Perform slow handling - after one second of inactivity, or after
            # 100 iterations of the main loop, as a safeguead.
            if skip_count >= 100 or await wait_ex(self.__event_heap_semaphore, 1):
                skip_count = 0
                if not self.__event_heap and self.__current_action is None:
                    self._logger.debug("No more events to process, will do Zigbee handling now")
                    if zigbee_action := self.__zigbee_helper.handle_zigbee_updates():
                        self.__current_action = await self.__execute_event(*zigbee_action)

                    if self.__current_action is None:
                        self.__zigbee_helper.handle_zigbeenodes_requests()
                    else:
                        # It may happen that the newly created task will be canceled
                        # immediately on the next iteration of the main loop and before
                        # getting scheduled. This may fail, hence a short wait.
                        await sleep_ms(100)
                self.__emit_clip_update_state(force_clip_update)
                force_clip_update = False
            else:
                skip_count += 1
            await self.__event_heap_semaphore.wait()

    async def on_event(self, component_event: ComponentEvent):
        """Ingests events and schedules them for dispatch in the order of priority."""
        events = [component_event] if isinstance(component_event, ComponentEvent) else component_event
        # Place all incoming events into the fast queue.
        self.__fast_queue += events
        self.__event_heap_semaphore.set()
