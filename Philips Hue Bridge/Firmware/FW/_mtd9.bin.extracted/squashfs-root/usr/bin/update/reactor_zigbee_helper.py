# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

from time import time as now_s

import config
from component import ComponentEvent
from component_zigbee import BroadcastGroup, ComponentZigbee
from frontend_zigbee import FrontendZigbee
from reactor_component_helper import ComponentHelper
from scheduler import Scheduler
from util.diagnostics import loggable
from util.misc import match, pretty_interval
from util.persistence import remap_keys

IPB_KEY_MAPPING = [
    ("m", "z_mac"),
    ("cv", "version"),
    ("dv", "z_downloaded_version"),
    ("nv", "z_transferred_version"),
    ("us", "z_update_state"),
    ("lt", "z_logical_type"),
    ("omc", "z_manufacturer_code"),
    ("pus", "z_battery_state"),
    ("it", "z_image_type"),
    ("r", "z_reachable"),
    ("ls", "z_last_seen"),
    ("wa", "z_workarounds"),
]


@loggable
class ZigbeeHelper:
    def __init__(self, components: ComponentHelper):
        self.__components = components
        self.__update_counter = 0
        self.__update_counter_new = 0
        self.__ipbridge_pid = 0
        self.__last_sense_requested = set()
        self.__last_poll_timstamp = 0

    def handle_install(self, event: ComponentEvent):
        """Handler for CLIP install triggers."""
        # The logic is as follows: iterate over all Zigbee components
        # that are ready to install, and flag them so they can be picked
        # up by the Zigbee update handler on the next iteration of the main loop.
        # Special handling for transfers in progress, in which case the transfer
        # has to be stopped.
        triggered = False
        for component in self.__components.iterate(match(ComponentZigbee, state="ready_to_install"), nested=True):
            self._logger.info("Zigbee component %s is ready to install, flagging", component.cid)
            component.update(recommended_mandatory=True, trigger_source=event.trigger_source)
            triggered = True
        # Stop the transfer, but only if we are going to install anything,
        # otherwise let the transfer to go on.
        if triggered and (
            component := self.__components.find_first(
                match(ComponentZigbee, state=("transfer_requested", "transferring")), nested=True
            )
        ):
            component.stop_transfer(event)
        if not triggered:
            self._logger.info("Ignored install trigger because there were no installable components.")
        event.accept()

    def handle_tick(self, _: ComponentEvent):
        # __last_poll_timestamp gets updated at the end of handle_sync
        if now_s() - self.__last_poll_timstamp > 24 * 60 * 60:
            Scheduler().schedule_event(
                ComponentEvent(command="zdb_change_trigger", update_counter=0, when=now_s(), force_clip_update=True)
            )
        Scheduler().schedule_event(ComponentEvent(command="tick", when=now_s() + 24 * 60 * 60))

    def handle_zdb_change_trigger(self, event: ComponentEvent):
        # If the ipbridge crashes and restarts, it will start the update counter
        # from 1 again, which will lead to all zigbee datastore notifications to
        # be ignored, until the counter value catches up with the last
        # counter value from before the crash.
        # Detect the ipbridge restart and reset the counter.
        if self.__ipbridge_pid != event.get("pid", self.__ipbridge_pid):
            if self.__ipbridge_pid:
                self._logger.info("Detected ipbridge restart, pid=%d, old_pid=%d", event.pid, self.__ipbridge_pid)
            self.__ipbridge_pid = event.pid
            self.__update_counter = 0
        # When we start up we send a fake datastore change notification
        # to ourselves with `update_counter` set to 0, so 0 has to be
        # accepted here.
        if event.update_counter == 0 or event.update_counter >= self.__update_counter:
            self.__update_counter_new = event.update_counter or 0
        else:
            self._logger.debug(
                "Out-of-order datastore trigger, counter=%d, last_counter=%d",
                event.update_counter,
                self.__update_counter,
            )
        event.accept()

    def handle_zigbeenodes_requests(self):
        if self.__update_counter_new == 0 or self.__update_counter_new > self.__update_counter:
            FrontendZigbee.request_node_list(
                update_counter=self.__update_counter if self.__update_counter_new != 0 else 0
            )

    def handle_zdb_delete_trigger(self, event: ComponentEvent):
        received_cids = set()
        nodes = event.get("nodes", [])
        for node in nodes:
            cid = config.zigbee_component_prefix + node.lower()
            received_cids.add(cid)
        self.__components.cleanup(received_cids)
        event.accept()

    def handle_sync(self, event: ComponentEvent):
        # There may be scenarios where we request the node list without being
        # triggered. In this case the update counter in the incoming list
        # will not get incremented, hence "greater or equal" instead of just "greater".
        if self.__update_counter_new == 0:
            self.__update_counter_new = 1
        if event.update_counter == 0 or event.update_counter >= self.__update_counter:
            self.__update_counter = event.update_counter
            for node in event.nodes:
                cid = config.zigbee_component_prefix + node["m"].lower()
                fields = remap_keys(IPB_KEY_MAPPING, node, wa=lambda wa: tuple(wa.split(",")))
                fake_event = ComponentEvent(
                    cid=cid,
                    command="sync",
                    source="ipbridge",
                    next_report_sequence=event.next_report_sequence,
                    **fields,
                )
                component: ComponentZigbee = self.__components.find_or_instantiate(from_event=fake_event)
                if component:
                    component.sync(fake_event)
            self.__last_poll_timstamp = now_s()
        else:
            self._logger.debug(
                "Out-of-order datastore update, counter=%d, last_counter=%d",
                event.update_counter,
                self.__update_counter,
            )
        event.accept()

    def __start_sense_awake(self, installable_nodes: list):
        macs = set(map(lambda c: c.z_mac, installable_nodes))
        if macs != self.__last_sense_requested:
            self._logger.debug("Requesting sense awake, macs=%s", macs)
            FrontendZigbee.request_sense_awake(macs)
            self.__last_sense_requested = macs

    def __stop_sense_awake(self):
        if self.__last_sense_requested:
            self._logger.debug("Stopping sense awake")
            FrontendZigbee.request_sense_awake(set())
            self.__last_sense_requested = set()

    def __pick_zigbee_component_to_update(self) -> tuple:
        if (
            bridge_component := self.__components.find(config.bridge_component)
        ) and bridge_component.clip_state() not in ("noupdates", "readytoinstall"):
            # We don"t want to interleave the bridge firmware download retries
            # with device updates.
            self._logger.debug("The bridge component is busy, device updates blocked")
        elif busy := self.__components.find_first(match(ComponentZigbee, BroadcastGroup, busy=True)):
            # Intermittent state, let the things settle first.
            self._logger.debug("At least one device is busy or not yet synced, cid=%s", busy.cid)
        else:
            # All components are idle and eager for some action.
            # Taking an action will make a component busy, meaning that
            # this branch will not be re-entered until all components are idle again.
            # N.B. An assumption is made that there exists only one broadcast group.
            component, command = None, None
            if broadcast_group := self.__components.find_first(match(BroadcastGroup, installable=True)):
                # Otherwise, if there are router components that have completed
                # transfers by the time they were flagged for installation then
                # issue a multicast to make them actuate updates.
                self._logger.debug(
                    "One or more router devices in the broadcast group can be installed, gid=%s", broadcast_group.cid
                )
                component, command = broadcast_group, "install"
                self.__stop_sense_awake()
            elif broadcast_group := self.__components.find_first(match(BroadcastGroup, updatable=True)):
                # Otherwise, if there"s still a router component for which a new
                # firmware is available then start transferring.
                self._logger.debug(
                    "One or more router devices in the broadcast group can be updated, gid=%s", broadcast_group.cid
                )
                updatable = [c for c in broadcast_group.components.values() if c.updatable()]
                updatable.sort()
                component, command = updatable[0], "fetch"
                self.__stop_sense_awake()
            # Lastly, all remaining node devices are updated one-by-one.
            elif installable_nodes := list(self.__components.iterate(match(ComponentZigbee, installable=True))):
                self._logger.debug("One or more end devices can be installed")
                # Order by last seen.
                installable_nodes.sort()
                candidate: ComponentZigbee = installable_nodes[0]
                self._logger.info(
                    "Installation candidate, cid=%s, age=%s",
                    candidate.cid,
                    pretty_interval(now_s() - max(candidate.z_last_seen, candidate.z_last_ping)),
                )
                # Is the device still listening after being woken up?
                if candidate.likely_alive():
                    component, command = candidate, "install"
                    self.__stop_sense_awake()
                else:
                    self.__start_sense_awake(installable_nodes)
            elif updatable_nodes := list(self.__components.iterate(match(ComponentZigbee, updatable=True))):
                self._logger.debug("One or more end devices can be updated")
                updatable_nodes.sort()
                component, command = updatable_nodes[0], "fetch"
                self.__stop_sense_awake()
            else:
                self.__stop_sense_awake()
            if component:
                self._logger.debug("Picked component %s, command=%s", component.cid, command)
                return component, command
            self._logger.debug("Nothing to do")
        return None, None

    def handle_zigbee_updates(self) -> tuple:
        component, command = self.__pick_zigbee_component_to_update()
        if component is not None:
            source = component.get("recommended_source", "unknown")
            event = ComponentEvent(
                command=command,
                cid=component.cid,
                source=source,
                version=component.get("recommended_version", "unknown"),
                block_request_delay=10 if source == "sideload" else config.dynamic["zigbee_block_request_delay"],
            )
            return component, event
        return None
