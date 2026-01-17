# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

import config
from component import ComponentEvent, ComponentObserver
from scheduler import Scheduler, after
from util.singleton import singleton


@singleton
class ObserverIot(ComponentObserver):
    def observe_component_registered(self, *_):
        Scheduler().schedule_event(
            ComponentEvent(command="report", kind="delta", when=after(seconds=config.delta_report_delay))
        )
