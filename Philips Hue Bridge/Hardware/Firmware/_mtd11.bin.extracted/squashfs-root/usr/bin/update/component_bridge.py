# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

import base64
from asyncio import CancelledError, sleep
from time import time as now_s

import config
from bridge.bootslot import Bootslot
from component import Component, ComponentEvent
from frontend_ipbridge import FrontendIpbridge
from frontend_sideload import FrontendSideload
from scheduler import Scheduler, after
from util.diagnostics import loggable
from util.misc import pretty_interval, random_window
from util.stream_wrapper import (
    CurlError,
    EndOfStreamError,
    HttpError,
    StreamChecksumError,
    StreamWrapperBase,
    stream_wrapper_from_reader,
    stream_wrapper_from_url,
)

from flasher import (
    FW2_ALLOW_COMMISSIONING_IF,
    FW2_ALLOW_DOWNGRADE,
    FW2_ALLOW_FACTORY_IF,
    FW2_ALLOW_TEST_IF,
    FW2_DONT_REBOOT,
    FW2_DONT_REQUIRE_WHITELIST,
    FW2_DONT_RESET_FN,
    SW_ERROR_GROUP_NAND,
    SW_ERROR_GROUP_SYSTEM,
    LibflasherError,
    LibflasherSpecialImage,
)


@loggable
class ComponentBridge(Component):
    def __init__(self):
        self.__bootslot = Bootslot()
        self.__frontend_sideload: FrontendSideload = None
        super().__init__(cid=config.bridge_component, version=self.__bootslot.active_version)
        self._register_event_handler(command="update", handler=self.__handle_update)
        self._register_event_handler(command="install", handler=self.__handle_install)
        self._register_event_handler(command="sync", handler=self.__handle_sync)
        self._register_event_handler(command="announce", handler=self.__handle_announce)
        self.update(clip_update_state="noupdates")
        self.__carry_over_flags = FW2_DONT_RESET_FN

    def extract_report_fields(self) -> dict:
        return self.remap(("cid", "cid"), ("version", "ver"))

    def extra_report_fields(self) -> dict:
        return {}

    def group(self) -> str:
        return None

    def idle(self) -> bool:
        # With both supported command handlers being blocking,
        # the only state when the main loop would be actually
        # able to call this, is by definition idle.
        return True

    def clip_state(self) -> str:
        return self.clip_update_state

    async def __handle_announce(self, event: ComponentEvent):
        if isinstance(event.frontend, FrontendSideload):
            self._logger.info("Received announce from FrontendSideload")
            self.__frontend_sideload = event.frontend

    async def __prepare_stream(self, event: ComponentEvent) -> StreamWrapperBase:
        """
        Instantiates the appropriate StreamWrapper depending on
        the update source.
        """
        if "url" in event:
            self._logger.info(
                "Filling bootslot %d with firmware %s from %s, md5=%s%s",
                self.__bootslot.inactive_index,
                event.version,
                event.url,
                event.checksum,
                f", retry={event.retry}" if "retry" in event else "",
            )
            return await stream_wrapper_from_url(event.url)
        if event.get("auth") != "sneaky":
            self._logger.info("Sideloading bootslot %d", self.__bootslot.inactive_index)
        else:
            self._logger.info("Processing special image")
        return await stream_wrapper_from_reader(event.reader, event.seed, event.end_sentinel)

    def __pre_update(self, event: ComponentEvent):
        self._logger.info("Executing update, source=%s, version=%s", event.source, event.version)
        self.update(transfer_started=now_s())
        self.update(
            **event.remap(
                ("version", "recommended_version"),
                ("url", "recommended_url"),
                ("checksum", "recommended_checksum"),
                ("mandatory", "recommended_mandatory"),
                ("source", "recommended_source"),
            )
        )
        if event.get("auth") != "sneaky":
            # Emit diagnostic messages, unless we are (most likely) dealing with a special image.
            if "retry" not in event:
                # Only emit `UpdateAvailable` for the originating update event,
                # but not for transfer retries.
                self.observe_update_available(event)
            self.observe_update_started(event)
            self.update(clip_update_state="transferring")

    def __post_update(self, event: ComponentEvent):
        self._logger.info(
            "Successfully transferred firmware image, version=%s, md5=%s%s",
            event.version,
            event.md5,
            f", retry={event.retry}" if "retry" in event else "",
        )
        event.update(**self.__bootslot.inactive_metadata.pick("soft_ecc_errors", "hard_ecc_errors", "bad_blocks"))

    def __trace_flags(self, event: ComponentEvent):
        self._logger.info(
            "Special flags, current=0x%02X, carry_over=0x%02X", event.special_flags, self.__carry_over_flags
        )

    def __handle_special_image(self, event: ComponentEvent, lse: LibflasherSpecialImage):
        self._logger.info("Received special image, options=0x%02X", lse.options)
        if any(
            interfaces := (
                bool(lse.options & FW2_ALLOW_TEST_IF),
                bool(lse.options & FW2_ALLOW_COMMISSIONING_IF),
                bool(lse.options & FW2_ALLOW_FACTORY_IF),
            )
        ):
            FrontendIpbridge.enable_interfaces(*interfaces)
            # To be absolutely sure that no funny business ever happens
            # at the kitting stations reset the flags to a "safe" value
            # and close the gates.
            event.update(special_flags=FW2_DONT_REBOOT)
            self.__carry_over_flags = FW2_DONT_RESET_FN
            self.__frontend_sideload.notify(options=0)
        else:
            # The sideloading frontend needs to be aware that the next
            # incoming request does not require a valid whitelist entry.
            self.__frontend_sideload.notify(options=lse.options & FW2_DONT_REQUIRE_WHITELIST)
            # We ourselves need to remember a few flags for the next incoming sideload.
            self.__carry_over_flags = lse.options & (FW2_ALLOW_DOWNGRADE | FW2_DONT_RESET_FN)
            # Those flags apply to the current session only.
            event.update(special_flags=lse.options & (FW2_DONT_REBOOT | FW2_DONT_RESET_FN))
        self.__trace_flags(event)

    def __handle_special_flags(self, event: ComponentEvent):
        if event.source != "sideload" or event.get("auth") == "whitelist":
            # For anything but a development sideload, do the following.
            # 1. Reset FW2_DONT_REQUIRE_WHITELIST flag at the gates.
            self.__frontend_sideload.notify(options=0)
            # 2. Set the current session flags to the default value.
            event.update(special_flags=FW2_DONT_RESET_FN)
        else:
            # For a development sideload set the current session
            # flags from the carry over flags.
            # No matter if the current image ends up being special,
            # the flags will get overwritten then.
            event.update(special_flags=self.__carry_over_flags)
        # In both cases the carry-over flags can be reset to the default value.
        self.__carry_over_flags = FW2_DONT_RESET_FN
        self.__trace_flags(event)

    def __handle_network_errors(self, event: ComponentEvent, exception: Exception):
        self._logger.info(
            "Fetching firmware failed due to %s(%s)%s",
            type(exception).__name__,
            str(exception),
            f", retry={event.retry}" if "retry" in event else "",
        )
        event.update(error=f"{type(exception).__name__}({str(exception)})")
        if isinstance(exception, HttpError):
            event.update(response_body=base64.b64encode(exception.body).decode())
        event.update(network_error=True)

    def __handle_other_errors(self, event: ComponentEvent, exception: Exception):
        event.update(error=f"{type(exception).__name__}({str(exception)})")
        if event.get("auth") == "sneaky":
            self._logger.error("Processing special image failed due to %s", event.error)
        else:
            self._logger.error("Flashing bootslot %d failed due to %s", self.__bootslot.inactive_index, event.error)
        if isinstance(exception, LibflasherError):
            event.update(error_code=exception.code)

    def __skip_update(self, event: ComponentEvent) -> bool:
        action = self.__assess_update(from_event=event)
        if action == "ignore":
            event.accept(error="ignored")
            return True
        if action == "duplicate":
            if event.get("mandatory", False):
                # The regular update that has been flashed already has become mandatory.
                event.update(special_flags=FW2_DONT_RESET_FN)
                self.__schedule_reboot(event)
            event.accept(error="ignored")
            return True
        return False

    async def __handle_update(self, event: ComponentEvent):
        def update_versions(version: str):
            # For sideloads we start with an "unknown" version, and only
            # learn the actual version at some point later when parsing
            # the firmware bundle. To avoid emitting diagnostic messages
            # with "unknown" version we update it as soon as we know it.
            # Note that this callback may still come if a network error
            # happened very early and before we saw any sections, in which
            # case `version` will be given as "unknown" as well, so we make
            # sure not to override valid IoT versions.
            if event.source == "sideload":
                self._logger.debug("Sideload version became known, version=%s", version)
                event.update(version=version)
                self.update(recommended_version=version)

        if self.__skip_update(event):
            return
        self.__handle_special_flags(event)
        try:
            self.__pre_update(event)
            try:
                async with await self.__prepare_stream(event) as stream:
                    await self.__bootslot.fill(
                        from_stream=stream,
                        source=event.source,
                        expected_md5=event.get("checksum"),
                        allow_downgrade=event.special_flags & FW2_ALLOW_DOWNGRADE,
                        version_callback=update_versions,
                    )
                    event.update(md5=stream.md5())
                self.__post_update(event)
            except LibflasherSpecialImage as lse:
                self.__handle_special_image(event, lse)
        except CancelledError:
            self._logger.info("Firmware fetching interrupted")
            event.update(error="canceled")
        except (OSError, HttpError, StreamChecksumError, EndOfStreamError, CurlError) as ne:
            self.__handle_network_errors(event, ne)
        except Exception as ex:
            self.__handle_other_errors(event, ex)
        finally:
            self.__finalise_update(event)

    def __finalise_update(self, event: ComponentEvent):
        if event.get("auth") != "sneaky":
            self.observe_update_ended(event)
            if self.__bootslot.inactive_metadata is not None:
                self._logger.info(
                    "Bridge updater task done, inactive bootslot contains %s from %s",
                    self.__bootslot.inactive_metadata.target_version,
                    self.__bootslot.inactive_metadata.source,
                )
                self.update(clip_update_state="readytoinstall", install_available=now_s())
            else:
                self._logger.info("Bridge updater task done, inactive bootslot is empty")
                self.update(clip_update_state="noupdates")
        if event.get("auth") != "sneaky" or "error" in event:
            # We need to make sure that FW2_DONT_REQUIRE_WHITELIST
            # flag is cleared. The only exception being just having
            # extracted it from a special image.
            self.__frontend_sideload.notify(options=0)
        self.__schedule_retry_or_reboot(event)
        event.accept()

    def __schedule_retry_or_reboot(self, event: ComponentEvent):
        """Schedules a follow-up action to the last update attempt."""
        if (network_error := event.get("network_error", False)) and event.source == "iot":
            # Retry failed IoT transfer.
            if (retry := event.get("retry", 0) + 1) < config.dynamic["iot_transfer_attempts"]:
                backoff = 3**retry
                backoff += random_window(backoff)
                self._logger.info("Will retry transfer in %s", pretty_interval(backoff))
                Scheduler().schedule_event(
                    ComponentEvent(
                        when=after(seconds=backoff),
                        retry=retry,
                        eid=event.eid,
                        command="update",
                        cid=event.cid,
                        source=event.source,
                        version=event.version,
                        url=event.url,
                        checksum=event.checksum,
                        mandatory=event.get("mandatory", False),
                    )
                )
                self.update(clip_update_state="readytoupdate")
            else:
                self._logger.warning(
                    "Exhausted all attempts trying to fetch firmware %s from %s", event.version, event.url
                )
        elif not network_error and event.get("mandatory", False):
            # Schedule a reboot, even if the flashing process failed.
            self.__schedule_reboot(event)

    def __schedule_reboot(self, event: ComponentEvent):
        if event.special_flags & FW2_DONT_REBOOT:
            self._logger.info("Reboot not scheduled, NO_REBOOT flag was set")
            # This flag will hint the sideloading frontend to give
            # the appropriate response to the client. Other than that
            # it doesn't affect any flow.
            event.update(reboot=False)
        elif "error_code" not in event or event.error_code & (SW_ERROR_GROUP_NAND | SW_ERROR_GROUP_SYSTEM):
            # Successful update or NAND or systenm error, reboot.
            reboot_flavour = "normal" if event.special_flags & FW2_DONT_RESET_FN else "factoryreset"
            self._logger.info("Reboot scheduled, flavour=%s", reboot_flavour)
            Scheduler().schedule_event(
                ComponentEvent(
                    when=after(seconds=0),
                    command="install",
                    cid=event.cid,
                    source=event.source,
                    version=event.version,
                    flavour=reboot_flavour,
                    trigger_source="mandatory",
                )
            )
        else:
            self._logger.info("Reboot not performed after failed update")

    async def __handle_install(self, event: ComponentEvent):
        if not self.__can_install(from_event=event):
            event.accept(error="ignored")
            return
        try:
            # Reboot if there"s anything in the inactive bootslot.
            install_needed = self.__bootslot.inactive_metadata is not None
            # Still reboot even if there"s nothing in the inactive bootslot, *unless* triggered by CLIP.
            reboot_needed = event.source != "clip"
            if install_needed:
                self.observe_install_started(event)
            if install_needed or reboot_needed:
                self.update(clip_update_state="installing")
                await self.__bootslot.install(event.flavour == "factoryreset")
            else:
                self._logger.info(
                    "Ignoring %s %s %s, trigger_source=%s", event.source, event.command, event.cid, event.trigger_source
                )
                event.update(error="ignored")
                return
        finally:
            event.accept()
        self._logger.info("Bridge installer task done, the main loop is blocked now")
        while True:
            await sleep(10)

    async def __handle_sync(self, event: ComponentEvent):
        self.update(version=event.version, report_sequence=event.next_report_sequence)
        self.observe_component_registered(event)
        if self.__bootslot.active_metadata:
            self.update(
                **self.__bootslot.active_metadata.remap(
                    ("install_started", "install_started"),
                    ("source", "recommended_source"),
                    ("target_version", "recommended_version"),
                )
            )
            fake_event = ComponentEvent(
                cid=config.bridge_component,
                source=self.__bootslot.active_metadata.source,
                version=self.__bootslot.active_metadata.target_version,
            )
            if self.__bootslot.active_metadata.target_version != self.__bootslot.active_version:
                fake_event.update(error="Expected to boot into version X, but booted into version Y instead")
            self.observe_install_ended(fake_event)
        event.accept()

    def __assess_update(self, from_event: "ComponentEvent") -> str:
        """
        Determines if the `update` event is applicable, i.e:
        - The retry event belongs to the retry chain originated by the latest update,
        - The update can override the content of the empty bootslot, following the priority rules.
        """
        # First deal with retry chains.
        if "eid" not in from_event:
            self._logger.warning(
                "Ignoring %s %s %s to %s, no event eid",
                from_event.source,
                from_event.command,
                self.cid,
                from_event.version,
            )
            return "ignore"
        if "retry" not in from_event:
            # Originating update event, note the eid.
            self.update(eid=from_event.eid)
        elif "eid" in self:
            if self.eid != from_event.eid:
                # Another update was triggered between two retries, drop
                # this retry chain.
                self._logger.info(
                    "Ignoring %s %s %s to %s, event eid (%s) does not match origin eid (%s)",
                    from_event.source,
                    from_event.command,
                    self.cid,
                    from_event.version,
                    from_event.eid,
                    self.eid,
                )
                return "ignore"
        else:
            self._logger.warning(
                "Ignoring %s %s %s to %s, no origin eid",
                from_event.source,
                from_event.command,
                self.cid,
                from_event.version,
            )
            return "ignore"
        # Now check the update source priority and versions.
        previous_source = "unknown"
        previous_version = "unknown"
        if self.__bootslot.inactive_metadata is not None:
            previous_source = self.__bootslot.inactive_metadata.source
            previous_version = self.__bootslot.inactive_metadata.target_version
        previous_weight = ComponentEvent.evaluate_weight(previous_source, ComponentEvent.source_weights())
        new_weight = ComponentEvent.evaluate_weight(from_event.source, ComponentEvent.source_weights())
        if previous_weight > new_weight:
            self._logger.info(
                "Ignoring %s %s %s to %s, previous source was %s",
                from_event.source,
                from_event.command,
                self.cid,
                from_event.version,
                previous_source,
            )
            return "ignore"
        # This is a special case, where we want to avoid repeatedly flashing
        # the inactive bootslot due to repeated identical IoT update events.
        if (previous_source, from_event.source) == ("iot", "iot") and previous_version == from_event.version:
            self._logger.info(
                "Ignoring %s %s %s to %s, inactive bootslot already contains this version",
                from_event.source,
                from_event.command,
                self.cid,
                from_event.version,
            )
            return "duplicate"
        return "accept"

    def __can_install(self, from_event: "ComponentEvent") -> bool:
        """
        Returns True if the inactive bootslot is empty, or has been flashed
        from the same source as the event source, therefore this `install` command
        is applicable. CLIP install trigger is always applicable.
        """
        if from_event.source == "clip":
            return True
        if self.__bootslot.inactive_metadata is None:
            return True
        if self.__bootslot.inactive_metadata.source == from_event.source:
            return True
        self._logger.info(
            "Ignoring %s %s %s to %s, previous source was %s",
            from_event.source,
            from_event.command,
            self.cid,
            from_event.version,
            self.recommended_source,
        )
        return False
