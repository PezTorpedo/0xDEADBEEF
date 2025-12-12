import asyncio

import config
import iot_monitor
import tokens
from app_config import application_config
from token_request import send_jwt_request
from utilities.backoff import BackOff
from utilities.event_logger import EventLogger
from utilities.state import State
from utilities.timer import Timer

from hueutils.queue import Queue

_event_queue = Queue()
_expired_apps = []


class States:
    BackingOff = "backing_off"
    WaitingForIotConnection = "wait_for_iot_connection"
    WaitForExpiredToken = "wait_for_expired_token"
    RequestingToken = "requesting_token"


class Events:
    BackoffExpired = "backoff_expired"
    IotConnection = "iot_connection"
    Received = "received"
    ConfigUpdated = "config_updated"
    Timeout = "timeout"


def _expire_backoff():
    _event_queue.put({'event': Events.BackoffExpired})


def _connection_callback(connected):
    _event_queue.put({'event': Events.IotConnection, 'connected': connected})


def _event_timeout():
    _event_queue.put({'event': Events.Timeout})


def _populate_expired_apps():
    # Only re-populate if the list is empty, so all tokens get a chance to be refreshed
    if len(_expired_apps) == 0:
        for app in application_config.jwt_enabled_apps():
            validity_left = tokens.get_validity_left(app)
            # check if jwt expires before token_status_check_period elapses
            if validity_left > config.token_status_check_period:
                tokens.set_validity(app, validity_left)
            else:
                _expired_apps.append(app)
    return len(_expired_apps) > 0


def _handle_backing_off(state, event):
    if event['event'] == Events.BackoffExpired:
        if iot_monitor.is_cloud_connected():
            expired = _populate_expired_apps()
            if expired:
                state.set(States.RequestingToken)
            else:
                state.set(States.WaitForExpiredToken)
        else:
            state.set(States.WaitingForIotConnection)


def _handle_wait_for_iot_connection(state, _event):
    # We do not need to check for a connected event, we are only interested in the connection status
    if iot_monitor.is_cloud_connected():
        expired = _populate_expired_apps()
        if expired:
            state.set(States.RequestingToken)
        else:
            state.set(States.WaitForExpiredToken)


def _handle_wait_for_expired_token(state, event):
    if event['event'] in [Events.Timeout, Events.ConfigUpdated]:
        expired = _populate_expired_apps()
        if expired:
            state.set(States.RequestingToken)
        else:
            state.set(States.WaitForExpiredToken)


def _handle_requesting_token(state, event):
    if event['event'] == Events.Received:
        expired = _populate_expired_apps()
        if expired:
            state.set(States.RequestingToken)
        else:
            state.set(States.WaitForExpiredToken)
    elif event['event'] == Events.Timeout:
        state.set(States.BackingOff)


def _handle_event(state, event):
    EventLogger().log_event(state.get(), event['event'], "no_app", iot_monitor.is_cloud_connected(), "")

    if state.get() == States.BackingOff:
        _handle_backing_off(state, event)
    elif state.get() == States.WaitingForIotConnection:
        _handle_wait_for_iot_connection(state, event)
    elif state.get() == States.WaitForExpiredToken:
        _handle_wait_for_expired_token(state, event)
    elif state.get() == States.RequestingToken:
        _handle_requesting_token(state, event)
    else:
        print(f"State unhandled: {state.get().value}")


async def handle_tokens(mqtt_conn):
    global _expired_apps
    _expired_apps = []
    backoff = BackOff(grow=config.state_initial_backoff, maximum=config.state_maximum_backoff, callback=_expire_backoff)
    # We might want to have two timers, one for polling and one for a timeout
    timer = Timer(config.token_status_check_period, _event_timeout)
    timer.start()

    def entry_requesting_token():
        # Taken an app from the list
        if len(_expired_apps) > 0:
            app = _expired_apps.pop()
            send_jwt_request(mqtt_conn, app)
            EventLogger().log_event(
                States.RequestingToken, "token_requested", app, iot_monitor.is_cloud_connected(), ""
            )
        timer.start()

    state = State(
        [States.BackingOff, States.WaitingForIotConnection, States.WaitForExpiredToken, States.RequestingToken],
        name="token",
    )
    state.set_entry(States.BackingOff, action=backoff.start)
    state.set_exit(States.BackingOff, action=backoff.stop)

    state.set_entry(States.WaitingForIotConnection, action=timer.start)
    state.set_exit(States.WaitingForIotConnection, action=timer.stop)

    state.set_entry(States.WaitForExpiredToken, action=timer.start)
    state.set_exit(States.WaitForExpiredToken, action=timer.stop)

    state.set_entry(States.RequestingToken, action=entry_requesting_token)

    state.set(States.BackingOff)

    iot_monitor.subscribe(_connection_callback)

    while True:
        try:
            event = await _event_queue.get()
            if event['event'] == Events.Received:
                backoff.reset()
            state.event(event)
            _handle_event(state, event)
            state.finish()
        except asyncio.CancelledError:
            EventLogger().log_event(
                "cancelled_error", "exception", "no_app", iot_monitor.is_cloud_connected(), "handle token cancelled"
            )
            break


def received_token():
    event = {'event': Events.Received}
    _event_queue.put(event)


def received_config():
    event = {'event': Events.ConfigUpdated}
    _event_queue.put(event)
