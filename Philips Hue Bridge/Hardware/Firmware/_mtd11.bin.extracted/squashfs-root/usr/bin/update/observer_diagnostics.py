# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

import json
from time import time as now_s

from component import Component, ComponentEvent, ComponentObserver
from util.diagnostics import loggable
from util.diagnostics_proxy import DiagnosticsProxy
from util.singleton import singleton


@singleton
@loggable
class ObserverDiagnostics(ComponentObserver):
    def __emit_trace_point(self, trace_point: str, target_entity: str, target_version: str, source: str, **kwargs):
        """Emits the "new style" observability trace point, as per the specification."""
        body = {
            "trace_point": trace_point,
            "target_entity": target_entity,
            "target_version": target_version,
            "source": source,
        }
        self._logger.debug("Emitting trace point, body=%s", body)
        if kwargs:
            body.update({"extra": json.dumps(kwargs)})
        try:
            DiagnosticsProxy().log("fw_update_diagnostics", json.dumps(body))
        except Exception:
            pass

    def observe_componentlist_sent(self, **kwargs):
        self.__emit_trace_point(
            trace_point="ComponentListSent", target_entity="", target_version="", source="", **kwargs
        )

    def observe_componentlist_received(self, **kwargs):
        self.__emit_trace_point(
            trace_point="ComponentListReceived", target_entity="", target_version="", source="", **kwargs
        )

    def observe_update_available(self, component: Component, event: ComponentEvent):
        self.__emit_trace_point(
            trace_point="UpdateAvailable",
            target_entity=event.cid,
            source=component.recommended_source,
            target_version=component.recommended_version,
            **component.extra_report_fields(),
        )

    def observe_update_started(self, component: Component, event: ComponentEvent):
        report_fields = {
            "trace_point": "TransferInitiated",
            "target_entity": component.cid,
            "target_version": component.recommended_version,
            "source": component.recommended_source,
        }
        report_fields.update(event.pick("url", "checksum", "retry"))
        report_fields.update(component.extra_report_fields())
        self.__emit_trace_point(**report_fields)

    def observe_update_ended(self, component: Component, event: ComponentEvent):
        report_fields = {
            "trace_point": "TransferComplete",
            "target_entity": component.cid,
            "target_version": component.recommended_version,
            "source": component.recommended_source,
            "duration": now_s() - component.transfer_started,
        }
        report_fields.update(
            event.pick(
                "soft_ecc_errors",
                "hard_ecc_errors",
                "bad_blocks",
                "fetched",
                "cached",
                "fetch_log",
                "retry",
                "response_body",
                "auth",
            )
        )
        report_fields.update(component.pick("transfer_attempt"))
        report_fields.update(component.extra_report_fields())
        if "error" in event:
            report_fields.update(trace_point="TransferFailed", error=event.error)
        self.__emit_trace_point(**report_fields)

    def observe_install_started(self, component: Component, event: ComponentEvent):
        # To investiage an issue, we add duration and duration_since_transfer
        report_fields = {
            "trace_point": "InstallInitiated",
            "target_entity": component.cid,
            "duration": int(now_s() - component.install_available) if "install_available" in component else -1,
            "duration_since_transfer": int(now_s() - component.transfer_started)
            if "transfer_started" in component
            else -1,
            "target_version": component.recommended_version,
            "source": component.recommended_source,
            "trigger_source": event.trigger_source,
        }
        report_fields.update(component.extra_report_fields())
        self.__emit_trace_point(**report_fields)

    def observe_install_ended(self, component: Component, event: ComponentEvent):
        report_fields = {
            "trace_point": "Installed",
            "target_entity": component.cid,
            "duration": int(now_s() - component.install_started),
            "source": component.recommended_source,
            "target_version": component.recommended_version,
        }
        report_fields.update(component.extra_report_fields())
        if "error" in event:
            report_fields.update(trace_point="InstallFailed", error=event.error)
        self.__emit_trace_point(**report_fields)
