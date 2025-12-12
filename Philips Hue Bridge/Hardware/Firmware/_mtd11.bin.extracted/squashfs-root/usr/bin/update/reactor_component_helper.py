# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

import config
from component import Component, ComponentEvent
from component_bridge import ComponentBridge
from component_zigbee import BroadcastGroup, ComponentZigbee, StinkyComponentError
from observer_diagnostics import ObserverDiagnostics
from observer_iot import ObserverIot
from util.diagnostics import loggable
from util.misc import match, neq


@loggable
class ComponentHelper:
    def __init__(self):
        self.__broadcast_groups = {
            "router": BroadcastGroup("router"),
        }
        self.__components = {g.cid: g for g in self.__broadcast_groups.values()}
        self.__stinky_components = set()

    def __instantiate(self, event: ComponentEvent) -> Component:
        """Instantiates a component for the given cid."""
        component = None
        if event.cid == config.bridge_component:
            component = ComponentBridge()
        elif event.cid.startswith(config.zigbee_component_prefix):
            try:
                component = ComponentZigbee(event)
                self.__stinky_components.discard(event.cid)
            except StinkyComponentError as sce:
                if event.cid not in self.__stinky_components:
                    self._logger.info("Component %s smells bad: %s", event.cid, str(sce))
                    self.__stinky_components.add(event.cid)
        else:
            self._logger.warning("Can't instantiate component %s", event.cid)
        if component:
            component.register_observer(ObserverDiagnostics()).register_observer(ObserverIot())
        return component

    def __register(self, component: Component):
        registry = self.__components
        if group := component.group():
            registry = self.__broadcast_groups[group].components
        registry[component.cid] = component

    def __find(self, cid: str) -> tuple:
        if cid in self.__components:
            return None, self.__components[cid]
        for group in self.__broadcast_groups.values():
            if cid in group.components:
                return group, group.components[cid]
        return None, None

    def __delitem__(self, cid: str):
        group, component = self.__find(cid)
        if group:
            del group.components[cid]
        elif component:
            del self.__components[cid]

    def find(self, cid: str) -> Component:
        """
        Finds a component by its identifier.

        Returns None if no such component is registered.
        """
        _, component = self.__find(cid)
        return component

    def iterate(self, predicate=lambda _: True, nested=False):
        """
        Iterates (in no particular order) over components
        for which `predicate` evaluates to True.

        If `nested` is False, only the top-level components are iterated over.

        Groups are treated as top-level components.
        """
        where = [self.__components]
        if nested:
            where += [g.components for g in self.__broadcast_groups.values()]
        for components in where:
            for component in components.values():
                if predicate(component):
                    yield component

    def find_first(self, predicate, nested=False) -> Component:
        """
        Returns the first (in no particular order) component
        for which `predicate` evaluates to True.

        If `nested` is False, only the top-level components are iterated over.

        Groups are considered as top-level components.
        """
        where = [self.__components]
        if nested:
            where += [g.components for g in self.__broadcast_groups.values()]
        for components in where:
            for component in components.values():
                if predicate(component):
                    return component
        return None

    def find_or_instantiate(self, from_event: ComponentEvent) -> Component:
        """
        Picks a component to dispatch the event to. Will instantiate
        the component if needed.
        """
        component = self.find(from_event.cid)
        if from_event.command == "sync":
            if not component:
                component = self.__instantiate(from_event)
                if component:
                    self._logger.info("Registered component %s, version=%s", from_event.cid, from_event.version)
                    self.__register(component)
        return component

    def cleanup(self, cids: set):
        """
        Removes all components which are present in the provided set of identifiers.
        """
        for cid in cids:
            self._logger.info("Deleted component %s", cid)
            del self[cid]

    def compute_clip_update_state(self) -> dict:
        if bridge_component := self.find_first(match(ComponentBridge)):
            bridge_state = bridge_component.clip_state()
            devices = self.iterate(match(ComponentZigbee, clip_state=neq("noupdates")), nested=True)
            device_states = {c.z_mac: c.clip_state() for c in devices}
            clip_state = {"bridge": bridge_state, "devices": device_states}
        else:
            clip_state = {"bridge": "noupdates", "devices": {}}
        self._logger.debug("CLIP update state is %s", clip_state)
        return clip_state
