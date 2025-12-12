# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

from time import ticks_diff

import config
from util.diagnostics import loggable
from util.eventing import AsynchronousEvent
from util.persistence import DataObject


@loggable
class Component(DataObject):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.update(report_sequence=0)
        self.__observers = []
        self.__event_handlers = {}

    def __match_event(self, event: "ComponentEvent", event_fields: dict) -> bool:
        for field, value in event_fields.items():
            if field not in event or event[field] != value:
                return False
        return True

    def __observe(self, handler: str, event: "ComponentEvent", unconditional=False):
        for observer, event_fields in self.__observers:
            if unconditional or self.__match_event(event, event_fields):
                getattr(observer, handler)(self, event)

    def _register_event_handler(self, command: str, handler):
        self.__event_handlers[command] = handler

    def extract_report_fields(self) -> dict:
        raise NotImplementedError("extract_report_fields")

    def group(self) -> str:
        raise NotImplementedError("group")

    async def dispatch(self, event: "ComponentEvent"):
        if event.command in self.__event_handlers:
            await self.__event_handlers[event.command](event)
        else:
            self._logger.warning("Ignoring unknown event, cid=%s, command=%s", self.cid, event.command)

    def register_observer(self, observer: "ComponentObserver", **kwargs) -> "Component":
        self.__observers.append((observer, kwargs))
        return self

    def observe_component_registered(self, event: "ComponentEvent"):
        self.__observe("observe_component_registered", event, unconditional=True)

    def observe_update_available(self, event: "ComponentEvent"):
        self.__observe("observe_update_available", event)

    def observe_update_started(self, event: "ComponentEvent"):
        self.__observe("observe_update_started", event)

    def observe_update_ended(self, event: "ComponentEvent"):
        self.__observe("observe_update_ended", event)

    def observe_install_started(self, event: "ComponentEvent"):
        self.__observe("observe_install_started", event)

    def observe_install_ended(self, event: "ComponentEvent"):
        self.__observe("observe_install_ended", event)


class ComponentEvent(AsynchronousEvent):
    """
    Carries a component event. Implements ordering (or weighting) semantics
    on top of all the functionality provided by the `AsynchronousEvent`.
    """

    def __lt__(self, other: "ComponentEvent") -> bool:
        for key, order in self.weights_in_order():
            own_weight = self.evaluate_weight(for_value=self[key], in_order=order)
            other_weight = self.evaluate_weight(for_value=other[key], in_order=order)
            # Events are queued in a min-heap, therefore we want the event
            # with the higher weight to be at the top of the heap.
            if own_weight > other_weight:
                return True
        return False

    def __eq__(self, other: "ComponentEvent") -> bool:
        fields = ["command", "source", "cid", "version"]
        values = self.pick(*fields)
        other_values = other.pick(*fields)
        return values == other_values

    def obsoleted_by(self, other: "ComponentEvent") -> bool:
        """
        Returns True if this event will be made redundant by
        the other event, scheduled after.
        """
        return (
            self.command == "report"
            and self.kind == "delta"
            and other.command == "report"
            and ticks_diff(other.when, self.when) < 60 * 5 * 1000
        )

    def asynchronous(self) -> bool:
        """
        Returns True if this is an asynchronous event, meaning that
        it runs in the background until completion or until interrupted,
        without blocking the main event loop. This is in contrast with
        synchronous events, which are executed on the main loop.
        """
        return (self.cid == config.bridge_component and self.command in ("update", "install")) or (
            self.cid.startswith(config.zigbee_component_prefix) and self.command == "fetch"
        )

    @staticmethod
    def copy(other: "ComponentEvent") -> "ComponentEvent":
        return ComponentEvent(**other.__dict__)

    @staticmethod
    def evaluate_weight(for_value: str, in_order: list) -> int:
        """
        Evaluates the weight of the provided value according to the
        provided weight list. If the value is not in the list it
        is assumed to have the lowest weight, i.e. it will be outweighed
        by any value with a listed weight.
        """
        try:
            return in_order.index(for_value)
        except ValueError:
            return -1

    @staticmethod
    def cid_weights() -> list:
        return [config.bridge_component, "any"]

    @staticmethod
    def source_weights() -> list:
        return ["portal", "iot", "sideload"]

    @staticmethod
    def command_weights() -> list:
        return ["sync", "install", "update", "transfer_ack", "fetch", "sense_awake"]

    @staticmethod
    def weights_in_order() -> list:
        """Cumulative event weights, component, then source, then command."""
        return [
            ("cid", ComponentEvent.cid_weights()),
            ("source", ComponentEvent.source_weights()),
            ("command", ComponentEvent.command_weights()),
        ]


class ComponentObserver:
    def observe_component_registered(self, component: Component, event: ComponentEvent):
        pass

    def observe_update_available(self, component: Component, event: ComponentEvent):
        pass

    def observe_update_started(self, component: Component, event: ComponentEvent):
        pass

    def observe_update_ended(self, component: Component, event: ComponentEvent):
        pass

    def observe_install_started(self, component: Component, event: ComponentEvent):
        pass

    def observe_install_ended(self, component: Component, event: ComponentEvent):
        pass
