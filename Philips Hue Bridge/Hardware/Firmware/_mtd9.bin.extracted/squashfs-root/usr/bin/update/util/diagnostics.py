# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

import json
from logging import CRITICAL, DEBUG, ERROR, INFO, WARNING, Handler, Logger, LogRecord, basicConfig, getLogger
from os import libc
from sys import exc_info, exit
from time import localtime

import config
from util.diagnostics_proxy import DiagnosticsProxy
from util.singleton import singleton

# The process exit code in case of a terminal error.
__FATAL_ERROR = 111

# From syslog.h
__SYSLOG_FACILITY_DAEMON = 3 << 3
__SYSLOG_OPTIONS_PID = 0x01
__SYSLOG_CRIT = 2
__SYSLOG_ERR = 3
__SYSLOG_WARNING = 4
__SYSLOG_INFO = 6
__SYSLOG_DEBUG = 7

__SYSLOG_LEVELS = {
    DEBUG: __SYSLOG_DEBUG,
    INFO: __SYSLOG_INFO,
    WARNING: __SYSLOG_WARNING,
    ERROR: __SYSLOG_ERR,
    CRITICAL: __SYSLOG_CRIT,
}

# void openlog(const char *ident, int option, int facility)
__openlog = libc.func("v", "openlog", "sii")

# void syslog(int priority, const char *format, ...)
# assumed to be only ever invoked as syslog(priority, "%s", message)
__syslog = libc.func("v", "syslog", "iss")

__use_syslog = False


def make_body(component: str, severity: str, message: str) -> str:
    return json.dumps(
        {
            "diagnostic_log": {
                "daemon": component,
                "severity": severity,
                "message": message,
            }
        }
    )


@singleton
class __LogHandler(Handler):
    """Handles logging to console of the syslog."""

    def __syslog_emitter(self, record: LogRecord):
        priority = __SYSLOG_LEVELS.get(record.levelno, __SYSLOG_INFO)
        __syslog(priority, "%s", f"{record.name}: {record.message}")

    def __stdout_emitter(self, record: LogRecord):
        now = localtime()
        print(f"{now.tm_hour:02}:{now.tm_min:02}:{now.tm_sec:02} {record.levelname:5} {record.name}: {record.message}")

    def emit(self, record: LogRecord):
        if __use_syslog:
            self.__syslog_emitter(record)
        else:
            self.__stdout_emitter(record)


@singleton
class __InsightHandler(Handler):
    """Handles logging to the remote "insight" endpoint."""

    def emit(self, record: LogRecord):
        if record.levelno in (CRITICAL, ERROR, WARNING):
            try:
                DiagnosticsProxy().log(
                    "diagnostic_log",
                    make_body(
                        component=record.name,
                        severity=record.levelname,
                        message=record.message,
                    ),
                )
            except Exception:
                pass


@singleton
class __CalamityHandler(Handler):
    """Handles terminal exceptions."""

    def emit(self, record: LogRecord):
        _, exception, _ = exc_info()
        if exception is not None and hasattr(exception, "terminal") and exception.terminal():
            try:
                DiagnosticsProxy().log(
                    "diagnostic_log",
                    make_body(
                        component=record.name,
                        severity="FATAL",
                        message=f"Shutting down due to {exception.__class__.__name__}({str(exception)})",
                    ),
                )
            except Exception:
                pass
            exit(__FATAL_ERROR)


def get_logger(name: str) -> Logger:
    """Returns a Logger object for the given module name."""
    logger = getLogger(name)
    logger.handlers = [__LogHandler(), __InsightHandler(), __CalamityHandler()]  # noqa: V101
    return logger


def initialise_logger(use_syslog: bool, verbose: bool):
    """
    Initialise the logging subsystem.

    This call is optional and the logging will still work with default
    settings if not called.

    Parameters:
        use_syslog: log to syslog instead of stdout.
        verbose: log more diagnostic messages.
    """
    global __use_syslog
    if use_syslog:
        __openlog(config.daemon_name, __SYSLOG_OPTIONS_PID, __SYSLOG_FACILITY_DAEMON)
        __use_syslog = True
    basicConfig(level=DEBUG if verbose else INFO)


def use_syslog() -> bool:
    """Returns True if logging to syslog is active."""
    return __use_syslog


def loggable(cls):
    cls._logger = get_logger(cls.__name__)
    return cls
