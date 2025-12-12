# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

from asyncio import CancelledError, sleep
from time import time as now_s

import config
from component import Component, ComponentEvent
from frontend_zigbee import FrontendZigbee
from micropython import const
from scheduler import Scheduler, after
from util.diagnostics import loggable
from util.misc import plu, pretty_interval, random_interval, random_window
from util.stream_wrapper import CurlError, HttpError, StreamChecksumError
from zigbee_fw_fetcher import ZigbeeFwFetcher

LT_ROUTER = const(0)
# LT_END_DEVICE = const(1)
# LT_END_DEVICE_SLOW = const(2)

US_NORMAL = const(0)
US_DOWNLOAD_IN_PROGRESS = const(1)
US_DOWNLOAD_COMPLETE = const(2)
US_WAITING_TO_UPGRADE = const(3)
US_COUNTDOWN = const(4)
# US_WAIT_FOR_MORE = const(5)
# US_UNKNOWN = const(99)

# BAT_OK = const(0)
BAT_LOW = const(1)
# BAT_UNKNOWN = const(99)


class StinkyComponentError(Exception):
    pass


@loggable
class BroadcastGroup(Component):
    def __init__(self, gid: str):
        super().__init__(cid=f"{gid}-group{id(self)}")
        self.components = {}
        self.__awaiting_broadcast_ack = False
        self._register_event_handler(command="install", handler=self.__handle_install)
        self._register_event_handler(command="install_ack", handler=self.__handle_install_ack)

    def busy(self) -> bool:
        return self.__awaiting_broadcast_ack or any(map(lambda c: c.busy(), self.components.values()))

    def updatable(self) -> bool:
        return any(map(lambda c: c.updatable(), self.components.values()))

    def installable(self) -> bool:
        return any(map(lambda c: c.installable(), self.components.values()))

    async def __handle_install(self, event: ComponentEvent):
        installable_components = 0
        # Let the group devices know that the groupcast has been issued for them.
        for component in self.components.values():
            # All components in the group will recieve the broadcast message,
            # regardless of the `mandatory` flag.
            if component.state == "ready_to_install":
                fake_event = ComponentEvent(cid=component.cid)
                fake_event.update(**event.pick("command", "source", "version"))
                await component.dispatch(fake_event)
                installable_components += 1
        if installable_components:
            self._logger.info("Issuing groupcast for %s, cid=%s", plu(installable_components, "component"), self.cid)
            FrontendZigbee.request_group_update(self.cid, 7)
            self.__awaiting_broadcast_ack = True
        event.accept()

    async def __handle_install_ack(self, event: ComponentEvent):
        """Handles the install trigger acknowledgement."""
        self._logger.info("Groupcast update, cid=%s, extra=`%s`", self.cid, event.pick("result", "cause"))
        if self.__awaiting_broadcast_ack:
            if event.result != "success":
                self._logger.warning("Zigbee groupcast request failed, result=%s, cause=%s", event.result, event.cause)
            self.__awaiting_broadcast_ack = False
        else:
            self._logger.info("Ignored event, cid=%s, command=%s", self.cid, event.command)
            event.update(error="ignored")
        event.accept()


@loggable
class ComponentZigbee(Component):
    def __init__(self, event: ComponentEvent):
        super().__init__(cid=event.cid)
        self.__sanity_check(event)
        self.update(**event.pick("z_logical_type", "z_manufacturer_code", "z_image_type", "z_mac", "z_workarounds"))
        self._logger.debug(
            "Instantiating component, cid=%s, mac=%s, manufacturer_code=%04x, image_type=%04x",
            self.cid,
            self.z_mac,
            int(self.z_manufacturer_code),
            int(self.z_image_type),
        )
        self._register_event_handler(command="update", handler=self.__handle_update)
        self._register_event_handler(command="fetch", handler=self.__handle_fetch)
        self._register_event_handler(command="transfer_ack", handler=self.__handle_transfer_ack)
        self._register_event_handler(command="install_ack", handler=self.__handle_install_ack)
        self._register_event_handler(command="sense_awake", handler=self.__handle_sense_awake)
        self._register_event_handler(command="test_force_expire_state", handler=self.__handle_test_force_expire_state)
        if self.z_logical_type == LT_ROUTER:
            self._register_event_handler(command="install", handler=self.__handle_group_install)
        else:
            self._register_event_handler(command="install", handler=self.__handle_install)
        self._register_event_handler(command="query", handler=self.__handle_query)
        self.__set_state("needs_sync", None)
        self.update(transfer_attempt=0, z_last_ping=0)

    def __sanity_check(self, event: ComponentEvent):
        """
        Checks if the device properties in sync event make
        sense and it"s safe to instantiate the component.
        """
        errors = []
        if int(event.version) == 0:
            errors.append("no version")
        if int(event.z_manufacturer_code) == 0xFFFF:
            errors.append("no manufacturer code")
        if int(event.z_image_type) == 0xFFFE:
            errors.append("no image type")
        if errors:
            raise StinkyComponentError(", ".join(errors))

    def extract_report_fields(self) -> dict:
        cid = f"{config.zigbee_component_prefix}{self.z_manufacturer_code:04x}_{self.z_image_type:04x}"
        if "z_workarounds" in self and "ph" in self.z_workarounds:
            cid = config.zigbee_component_prefix + "{z_manufacturer_code:04x}_{z_image_type:04x}_wa".format(
                **self.__dict__
            )
        else:
            cid = config.zigbee_component_prefix + "{z_manufacturer_code:04x}_{z_image_type:04x}".format(
                **self.__dict__
            )
        return {"cid": cid, "ver": str(self.version), "mac": self.z_mac}

    def extra_report_fields(self) -> dict:
        return self.remap(
            ("z_manufacturer_code", "manufacturer_code"),
            ("z_image_type", "image_type"),
            ("version", "source_version"),
            ("z_reachable", "reachable"),
            ("z_battery_state", "battery"),
            z_manufacturer_code=lambda mc: f"{mc:04x}",  # pylint: disable=unnecessary-lambda
            z_image_type=lambda it: f"{it:04x}",  # pylint: disable=unnecessary-lambda
        )

    def clip_state(self) -> str:
        if self.state == "error":
            return "error"
        if self.state == "update_available":
            return "readytoupdate"
        if self.state in ("fetching", "fetched", "transfer_requested", "transferring"):
            return "transferring"
        if self.state == "ready_to_install":
            return "installing" if self.get("recommended_mandatory", False) else "readytoinstall"
        if self.state in ("install_requested", "installing"):
            return "installing"
        return "noupdates"

    def group(self) -> str:
        return "router" if self.z_logical_type == LT_ROUTER else None

    def busy(self) -> bool:
        return self.state in (
            "fetching",
            "fetched",
            "transfer_requested",
            "transferring",
            "install_requested",
            "installing",
            "needs_sync",
        )

    def idle(self) -> bool:
        return self.state in ("up_to_date", "update_available", "ready_to_install")

    def updatable(self) -> bool:
        sun_is_shining = self.z_reachable and self.z_battery_state != BAT_LOW
        weather_is_good = self.state == "update_available" and self.transfer_attempt < config.zigbee_transfer_retries
        return sun_is_shining and weather_is_good

    def installable(self) -> bool:
        sun_is_shining = self.z_reachable and self.z_battery_state != BAT_LOW
        weather_is_good = self.state == "ready_to_install" and self.get("recommended_mandatory", False)
        return sun_is_shining and weather_is_good

    def likely_alive(self) -> bool:
        return now_s() - max(self.z_last_seen, self.z_last_ping) <= 7

    def __lt__(self, other: Component) -> bool:
        """
        Determines if this component should be updated (or installed) before
        the other component.
        """
        # Prioritise transfers for devices with mandatory updates.
        if self.get("recommended_mandatory", False) and not other.get("recommended_mandatory", False):
            return True
        if not self.get("recommended_mandatory", False) and other.get("recommended_mandatory", False):
            return False
        # Both are mandatory, or both are non-mandatory; pick the one seen more recently.
        return max(self.z_last_seen, self.z_last_ping) > max(other.z_last_seen, other.z_last_ping)

    def __set_state_timeout(self, state: str, timeout_override: float):
        del self["state_timeout"]
        if timeout_override is not None:
            self.update(state_timeout=timeout_override)
        else:
            if state == "error":
                # From 1 hour to 24 hours.
                self.update(state_timeout=60 * 60 + random_interval(60 * 60 * 23))
            elif state in ("transfer_requested", "install_requested"):
                # Those states expect a command acknowledgement from ipbridge, and may
                # only timeout if ipbridge has crashed. Hence the short timeout.
                self.update(state_timeout=60)
            elif state == "installing":
                self.update(state_timeout=60 * 25)
            elif state == "transferring":
                self.update(state_timeout=60 * 60 * 5)

    def __trigger_observers(self, event: ComponentEvent, state: str, previous_state: str):
        if state in ("error", "update_available") and previous_state in (
            "fetching",
            "fetched",
            "transfer_requested",
            "transferring",
        ):
            self.complement(transfer_started=now_s())
            self.observe_update_ended(event)
        elif state == "error" and previous_state in ("install_requested", "installing"):
            self.complement(install_started=now_s())
            self.observe_install_ended(event)
        elif state == "update_available":
            self.observe_update_available(event)
        elif state == "fetching":
            self.update(transfer_started=now_s())
            self.observe_update_started(event)
        elif state == "ready_to_install":
            self.complement(transfer_started=now_s())
            self.observe_update_ended(event)
        elif state == "install_requested" or (self.z_logical_type == LT_ROUTER and state == "installing"):
            self.update(install_started=now_s())
            self.observe_install_started(event)
        elif state == "up_to_date" and previous_state == "installing":
            self.complement(install_started=now_s())
            self.observe_install_ended(event)

    def __remove_potentially_bad_image_from_cache(self, state: str, previous_state: str):
        """
        Removes the downloaded firmware image from the cache
        in case transfer of installation have just failed.
        """
        if state == "error" and previous_state in (
            "fetching",
            "fetched",
            "transfer_requested",
            "transferring",
            "install_requested",
            "installing",
        ):
            if "recommended_checksum" in self:
                ZigbeeFwFetcher().delete(self.recommended_checksum)

    def __set_state(self, state: str, event: ComponentEvent, timeout_override: float = None) -> str:
        previous_state = self.get("state")
        if previous_state != state:
            duration = ""
            if "state_timestamp" in self:
                duration_s = now_s() - self.state_timestamp
                duration = f" after {pretty_interval(duration_s)}"
            self._logger.info(
                "State change%s, cid=%s, %s -> %s, extra=%s",
                duration,
                self.cid,
                self.get("state", "instantiated"),
                state,
                self.pick("version", "recommended_version"),
            )
            self.update(state=state, state_timestamp=now_s())
            self.__set_state_timeout(state, timeout_override)
            self.__trigger_observers(event, state, previous_state)
            self.__remove_potentially_bad_image_from_cache(state, previous_state)
        if state == "up_to_date":
            # It is very likely that the component version has changed,
            # update the report sequence and trigger a delta report.
            self._logger.info("Will include in report, sequence=%d", event.next_report_sequence)
            self.update(report_sequence=event.next_report_sequence)
            self.observe_component_registered(event)
        if state in ("up_to_date", "error", "needs_sync"):
            self.delete(
                "recommended_version",
                "recommended_url",
                "recommended_checksum",
                "recommended_mandatory",
                "recommended_source",
                "trigger_source",
            )
        if state == "transferring":
            self.delete("transfer_ack_gate")
        return previous_state

    async def __handle_sense_awake(self, event: ComponentEvent):
        self._logger.debug("Sense awake, cid=%s, age=%s", self.cid, pretty_interval(now_s() - event.awake_timestamp))
        self.update(z_last_ping=event.awake_timestamp)
        event.accept()

    async def __handle_fetch(self, event: ComponentEvent):
        """
        Fetches the firmware image and passes it over to ipbridge
        to perform the Zigbee transfer.
        """
        event.update(**self.remap(("recommended_url", "url"), ("recommended_checksum", "checksum")))
        self.__set_state("fetching", event)
        self.update(transfer_attempt=self.transfer_attempt + 1)
        exception_log = []
        try:
            if int(self.get("z_transferred_version", 0)) != int(self.recommended_version):
                # Normal path: the device has no downloaded firmware, or it has downloaded
                # some other version. Fetch and transfer.
                total_attempts = config.dynamic["iot_transfer_attempts"]
                while (attempt := len(exception_log)) < total_attempts:
                    if attempt:
                        backoff = 2 ** (attempt - 1)
                        backoff += random_window(backoff)
                        self._logger.info("Backing off for %s, cid=%s", pretty_interval(backoff), self.cid)
                        await sleep(backoff)
                    try:
                        self._logger.info(
                            "Fetching firmware, cid=%s, attempt=%d, extra=%s",
                            self.cid,
                            attempt + 1,
                            self.pick("version", "recommended_version"),
                        )
                        fetched_destination, cached = await ZigbeeFwFetcher().fetch(
                            self.recommended_url, self.recommended_checksum
                        )
                        event.update(fetched=True, cached=cached)
                        self.__set_state("fetched", event)
                        extra = self.pick("version", "recommended_version")
                        extra.update(block_request_delay=event.block_request_delay)
                        self._logger.info(
                            "Transferring firmware, cid=%s, attempt=%d, extra=%s",
                            self.cid,
                            self.transfer_attempt,
                            extra,
                        )
                        FrontendZigbee.request_transfer_image(
                            request_id=self.cid,
                            mac=self.z_mac,
                            path=fetched_destination,
                            version=int(self.recommended_version),
                            block_request_delay=event.block_request_delay,
                        )
                        self.__set_state("transfer_requested", event)
                        break
                    except (OSError, HttpError, StreamChecksumError, CurlError) as e:
                        self._logger.info(
                            "Fetching firmware failed due to %s(%s), cid=%s, attempt=%d",
                            type(e).__name__,
                            str(e),
                            self.cid,
                            attempt + 1,
                        )
                        exception_log += [e]
                if attempt == total_attempts:
                    raise exception_log.pop()
            else:
                # Short path: the device already has the exact same firmware downloaded.
                self._logger.info(
                    "Firmware was already downloaded to device, cid=%s, extra=%s",
                    self.cid,
                    self.pick("version", "recommended_version", "z_downloaded_version"),
                )
                event.update(fetched=False)
                self.__set_state("fetched", event)
                self.__set_state("ready_to_install", event)
        except CancelledError:
            self._logger.info("Firmware fetching interrupted")
            event.update(error="interrupted", fetch_attempt=len(exception_log) + 1)
            if exception_log:
                event.update(fetch_log=", ".join([f"{type(e).__name__}({str(e)})" for e in exception_log]))
            self.__set_state("error", event, timeout_override=1)
        except Exception as ex:
            self._logger.error(
                "Fetching firmware for component %s failed due to %s(%s)", self.cid, type(ex).__name__, str(ex)
            )
            event.update(error=f"{type(ex).__name__}({str(ex)})", fetch_attempt=len(exception_log) + 1)
            if exception_log:
                event.update(fetch_log=", ".join([f"{type(e).__name__}({str(e)})" for e in exception_log]))
            self.__set_state("error", event)
        finally:
            event.accept()

    async def __handle_transfer_ack(self, event: ComponentEvent):
        """Handles the Zigbee transfer acknowledgement."""
        self._logger.info("Transfer update, cid=%s, extra=`%s`", self.cid, event.pick("result", "cause"))
        if self.state == "transfer_requested":
            if event.result == "started":
                self.__set_state("transferring", event)
            else:
                event.update(error=f"Zigbee transfer request failed, result={event.result}, cause={event.cause}")
                self.__set_state("error", event)
        elif self.state == "transferring" and event.result == "transferred":
            # Two confirmations are needed to transit from Transferring
            # to Ready To Install. As those arrive in a non-deterministic order,
            # we use a gate approach, where both have to arrive before the gate opens.
            self.update(transfer_ack_gate=self.get("transfer_ack_gate", 0) | 1)
            if self.transfer_ack_gate == 3:
                self._logger.info(
                    "Device completed image transfer (transfer ack last), cid=%s, extra=%s",
                    self.cid,
                    self.pick("z_transferred_version"),
                )
                self.__set_state("ready_to_install", event)
            else:
                self._logger.info("Zigbee transfer complete, still need sync to confirm, cid=%s", self.cid)
        elif self.state == "transferring" and event.result != "transferred":
            event.update(error=f"Zigbee transfer failed, result={event.result}, cause={event.cause}")
            # Either "Timeout, router", or "Timeout, enddevice".
            if event.cause.startswith("Timeout"):
                self._logger.info("Device became unreachable during transfer, will retry ASAP, cid=%s", self.cid)
                # Decrement the transfer attempt, so not to count this
                # scenario towards the transfer attempt limit.
                self.update(transfer_attempt=self.transfer_attempt - 1)
                self.__set_state("error", event, timeout_override=0.1)
            else:
                self.__set_state("error", event)
        else:
            self._logger.info("Ignoring event `%s`, cid=%s, state=%s", event.command, self.cid, self.state)
            event.update(error="ignored")
        event.accept()

    async def __handle_update(self, event: ComponentEvent):
        """
        Handles the cloud update event and switches to `ready_to_install`
        state if needed.
        """
        action = "ignore"
        version = self.get("recommended_version", self.version)
        mandatory = self.get("recommended_mandatory", False)
        version_bump = int(event.version) > int(version)
        mandatory_bump = event.mandatory and not mandatory
        if version_bump and self.state in ("up_to_date", "ready_to_install"):
            # The recommended version received from the cloud is higher
            # than either the component current version or previously
            # received recommended version. Switch to `update_available`.
            action = "switch"
        elif version_bump and self.state == "update_available":
            # The recommended version received from the cloud is higher
            # than either the component current version or previously
            # received recommended version. Stay in `update_available`.
            action = "stay"
        elif mandatory_bump and self.state in ("update_available", "ready_to_install"):
            # The recommended version stayed the same, but the mandatory
            # flag changed. Stay in the current state.
            action = "stay"
        if action in ("stay", "switch"):
            self.update(
                **event.remap(
                    ("version", "recommended_version"),
                    ("url", "recommended_url"),
                    ("checksum", "recommended_checksum"),
                    ("mandatory", "recommended_mandatory"),
                    ("source", "recommended_source"),
                )
            )
            self._logger.info(
                "Recommended update, cid=%s, extra=%s",
                self.cid,
                self.pick("version", "recommended_version", "recommended_mandatory"),
            )
            if action == "switch":
                self.__set_state("update_available", event)
            if event.mandatory:
                self.update(trigger_source="mandatory")
        if action == "ignore":
            # We are in a wrong state; or nothing changed, for example as a result
            # of a duplicate `update` event; or the combination of fields doesn"t make sense.
            self._logger.debug("Ignored event, cid=%s, command=%s, state=%s", self.cid, event.command, self.state)
            event.update(error="ignored")
        event.accept()

    async def __handle_group_install(self, event: ComponentEvent):
        """
        Handles the install trigger for router devices.

        This simply means setting the state to Installing, as the actual
        installation is performed by the parent BroadcastGroup.
        """
        self.complement(trigger_source="broadcast")
        event.update(trigger_source=self.trigger_source)
        self.__set_state("installing", event)
        event.accept()

    async def __handle_install(self, event: ComponentEvent):
        """
        Handles the install trigger by requesting bootslot switch for
        the matching Zigbee node.
        """
        self._logger.info(
            "Installing firmware cid=%s, extra=%s",
            self.cid,
            self.pick("version", "recommended_version", "trigger_source"),
        )
        FrontendZigbee.request_unicast_update(self.cid, self.z_mac)
        event.update(trigger_source=self.trigger_source)
        self.__set_state("install_requested", event)
        event.accept()

    async def __handle_install_ack(self, event: ComponentEvent):
        """Handles the install trigger acknowledgement."""
        self._logger.info("Install update, cid=%s, extra=`%s`", self.cid, event.pick("result", "cause"))
        if self.state == "install_requested":
            if event.result == "success":
                self.__set_state("installing", event)
            else:
                event.update(error=f"Zigbee install request failed, result={event.result}, cause={event.cause}")
                self.__set_state("error", event)
        else:
            self._logger.info("Ignored event, cid=%s, command=%s, state=%s", self.cid, event.command, self.state)
            event.update(error="ignored")
        event.accept()

    async def __handle_test_force_expire_state(self, event: ComponentEvent):
        if self.state == event.expected_state and self.state in ("transferring", "installing", "error"):
            self._logger.info("Forced timeout expiration, cid=%s, state=%s", self.cid, self.state)
            self.update(state_timeout=0)
            Scheduler().schedule_event(
                ComponentEvent(command="zdb_change_trigger", update_counter=0, when=after(seconds=0))
            )
            Scheduler().schedule_event(
                ComponentEvent(command="zdb_change_trigger", update_counter=0, when=after(seconds=5))
            )
        else:
            self._logger.info(
                "Ignored event, cid=%s, command=%s, state=%s, expected_state=%s",
                self.cid,
                event.command,
                self.state,
                event.expected_state,
            )
        event.accept()

    async def __handle_query(self, event: ComponentEvent):
        event.accept(
            **self.remap(
                "version",
                "recommended_version",
                "state",
                ("z_manufacturer_code", "manufacturer_code"),
                ("z_image_type", "image_type"),
                ("z_reachable", "reachable"),
                ("z_battery_state", "battery"),
            )
        )

    def stop_transfer(self, event: ComponentEvent):
        if self.state in ("transfer_requested", "transferring"):
            self._logger.info("Stopping transfer, cid=%s, state=%s", self.cid, self.state)
            self.__set_state("error", ComponentEvent.copy(event).update(error="interrupted"), timeout_override=1)

    def __handle_timed_transitions(self, event: ComponentEvent, *args) -> bool:
        """
        Determines if the current state has timed out and switches
        to Error state, _unless_ the current state is in the exception list.

        Returns a flag indicating if a timeout has occured.
        """
        timeout_flag = False
        current_state_timeout_s = self.get("state_timeout")
        if current_state_timeout_s is not None:
            current_state_duration_s = now_s() - self.state_timestamp
            current_state_remaining_s = current_state_timeout_s - current_state_duration_s
            if current_state_remaining_s <= 0:
                if self.state == "error":
                    # For consistency, always transit to Needs Sync from Error.
                    self.__set_state("needs_sync", event)
                    FrontendZigbee.request_ota_attributes(self.cid, self.z_mac)
                elif self.state not in args:
                    # The current state has expired, so transit through the Error state.
                    # This is needed for the diagnostic messages to get emitted.
                    event.update(error=f"State {self.state} timed out")
                    self.__set_state("error", event)
                timeout_flag = True
            elif self.state not in args:
                self._logger.debug(
                    "Component %s is in timed state %s for another %s, ignored event %s",
                    self.cid,
                    self.state,
                    pretty_interval(current_state_remaining_s),
                    event.pick("command", "source"),
                )
        return timeout_flag

    def sync(self, event: ComponentEvent):  # noqa: C901
        """Synchronises the component state with the zigbee node state."""
        # We want to always keep those fields up to date.
        self.update(**event.pick("z_reachable", "z_last_seen", "z_battery_state"))
        if event.z_update_state in (US_DOWNLOAD_COMPLETE, US_WAITING_TO_UPGRADE):
            # This field is set as soon as the device starts transferring, but
            # we are only interested in it when once the transfer has completed.
            self.update(z_transferred_version=event.z_transferred_version)
        else:
            self.update(z_transferred_version=0)
        handled = False
        # The system logging level is not propagated to individual loggers,
        # nor it is exposed globally, so we can't write this condition as
        # `if self._logger.level == DEBUG`.
        if config.fixed["verbose"]:
            self._logger.debug(
                "Sync event, cid=%s, state=%s, versions=%s, extra=%s",
                self.cid,
                self.state,
                self.pick("version", "recommended_version", "recommended_source", "recommended_mandatory"),
                event.pick("version", "z_reachable", "z_battery_state", "z_transferred_version", "z_update_state"),
            )
        # Installing state will not transit to Error automatically, because
        # it requires special handling.
        if not (timed_out := self.__handle_timed_transitions(event, "installing")) or self.state == "installing":
            if self.state == "needs_sync":
                if event.z_update_state in (
                    US_NORMAL,
                    US_DOWNLOAD_COMPLETE,
                    US_WAITING_TO_UPGRADE,
                    US_DOWNLOAD_IN_PROGRESS,
                    US_COUNTDOWN,
                ):
                    self._logger.info(
                        "Component version updated, cid=%s, %s -> %s", self.cid, self.get("version"), event.version
                    )
                    self.update(version=event.version)
                    self.__set_state("up_to_date", event)
                    handled = True
                else:
                    self._logger.warning(
                        "Problem syncing device, cid=%s, z_update_state=%s", self.cid, event.z_update_state
                    )
                    self.update(version=event.version)
                    self.__set_state("error", event)
                    handled = True
            elif self.state == "transferring" and event.z_update_state in (US_DOWNLOAD_COMPLETE, US_WAITING_TO_UPGRADE):
                # Two confirmations are needed to transit from Transferring
                # to Ready To Install. As those arrive in a non-deterministic order,
                # we use a gate approach, where both have to arrive before the gate opens.
                self.update(transfer_ack_gate=self.get("transfer_ack_gate", 0) | 2)
                if self.transfer_ack_gate == 3:
                    self._logger.info(
                        "Device completed image transfer (sync last), cid=%s, extra=%s",
                        self.cid,
                        self.pick("z_transferred_version"),
                    )
                    self.__set_state("ready_to_install", event)
                    handled = True
                else:
                    self._logger.info(
                        "Device may have completed image transfer, still need transfer ack, cid=%s, extra=%s",
                        self.cid,
                        self.pick("z_transferred_version"),
                    )
            elif self.state == "installing":
                if event.z_update_state == US_NORMAL and int(event.version) == int(self.recommended_version):
                    # Handle transition out of Installing state. This can only happen
                    # if the device update state is Normal and the device version
                    # is equal to the previously set recommended version.
                    extra = ""
                    if event.z_image_type != self.z_image_type:
                        extra = f", old_image_type={self.z_image_type:04x}, new_image_type={event.z_image_type:04x}"
                    self._logger.info("Install ended, cid=%s, new_version=%s%s", self.cid, event.version, extra)
                    self.update(version=event.version, z_image_type=event.z_image_type, transfer_attempt=0)
                    self.__set_state("up_to_date", event)
                    handled = True
                elif timed_out:
                    # Be mindful of a race condition where the zigbee node list is issued right before
                    # we told the device to install, but arrives after the device state
                    # has been switched to Installing. In this case we would see the "old"
                    # version and think the device has failed installing.
                    # We work around this by ignoring updates with mismatching version
                    # for this device for a short while after switching to Installing state.
                    event.update(
                        error="Expected to see version X, but saw version Y instead", version=self.recommended_version
                    )
                    self.update(version=event.version, transfer_attempt=0)
                    self.__set_state("error", event)
                    handled = True
            elif self.state in ("up_to_date", "update_available") and event.version != self.version:
                # There are still corner cases where the device version can change
                # when we are not expecting it.
                self._logger.info(
                    "Component version changed unexpectedly, cid=%s, %s -> %s",
                    self.cid,
                    self.get("version"),
                    event.version,
                )
                self.update(version=event.version)
                # Will take care or clearing the recommended update state and
                # requesting a delta report.
                self.__set_state("up_to_date", event)
                handled = True
            elif self.state in ("up_to_date", "update_available") and event.z_image_type != self.z_image_type:
                # There are still corner cases where the device image type can change
                # when we are not expecting it.
                self._logger.info(
                    "Component image type changed unexpectedly, cid=%s, %04x -> %04x",
                    self.cid,
                    int(self.z_image_type),
                    int(event.z_image_type),
                )
                self.update(z_image_type=event.z_image_type)
                # Will take care or clearing the recommended update state and
                # requesting a delta report.
                self.__set_state("up_to_date", event)
                handled = True
            if not handled:
                self._logger.debug(
                    "Ignored sync event, cid=%s, state=%s, update_state=%s", self.cid, self.state, event.z_update_state
                )
        if not handled:
            event.update(error="ignored")
        event.accept()
