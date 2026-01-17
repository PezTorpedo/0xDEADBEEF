# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

from time import time as now_s

import config
from component import ComponentEvent, ComponentObserver
from scheduler import Scheduler
from util.singleton import singleton


@singleton
class ObserverIot(ComponentObserver):
    def observe_component_registered(self, *_):
        Scheduler().schedule_event(
            ComponentEvent(command="report", kind="delta", when=now_s() + config.delta_report_delay)
        )
