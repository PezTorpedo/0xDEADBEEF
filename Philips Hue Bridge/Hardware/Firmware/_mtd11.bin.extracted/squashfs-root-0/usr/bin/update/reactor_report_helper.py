# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

import config
from component import ComponentEvent
from component_bridge import ComponentBridge
from component_zigbee import ComponentZigbee
from frontend_iot import FrontendIot
from observer_diagnostics import ObserverDiagnostics
from reactor_component_helper import ComponentHelper
from scheduler import Scheduler
from util.calculate_report import calculate_next_report_time
from util.diagnostics import loggable
from util.misc import gt, match


@loggable
class ReportHelper:
    def __init__(self, components: ComponentHelper):
        self.__components = components
        self.sequence = 0

    def __schedule_next_report(self):
        # Exactly 24 hours from now.
        next_time = calculate_next_report_time()
        Scheduler().schedule_event(ComponentEvent(command="report", kind="daily", when=next_time))

    def handle_iot_connected(self, event: ComponentEvent):
        schedule = calculate_next_report_time(resync=True)
        Scheduler().schedule_event(ComponentEvent(command="report", kind="daily", when=schedule))
        event.accept()

    def handle_component_report(self, event: ComponentEvent):
        """Handler for the scheduled report requests."""
        if event.kind == "delta":
            # Delta report, include only updated components.
            predicate = match(ComponentBridge, ComponentZigbee, report_sequence=gt(self.sequence), idle=True)
        else:
            # Daily or manual, include all components.
            predicate = match(ComponentBridge, ComponentZigbee, idle=True)
        components = list(self.__components.iterate(predicate=predicate, nested=True))
        self.sequence += 1
        if components:
            self._logger.info(
                "Sending out report for %d components, kind=%s, sequence=%d", len(components), event.kind, self.sequence
            )
            if config.fixed["verbose"]:
                self._logger.debug("Included in report: %s", [f"{c.cid}@{c.version}" for c in components])
            FrontendIot.report([c.extract_report_fields() for c in components])
            ObserverDiagnostics().observe_componentlist_sent(component_count=len(components), sequence=self.sequence)

        else:
            self._logger.info("Nothing to do, kind=%s, sequence=%d", event.kind, self.sequence)
        if event.kind == "daily":
            self.__schedule_next_report()
        event.accept()
