import asyncio

import config
import iot_monitor
import token_sync
from device_state import send_state
from utilities.backoff import BackOff
from utilities.state import State
from utilities.timer import Timer

from hueutils.queue import Queue

_event_queue = Queue()


class States:
    BackingOff = "backing_off"
    WaitingForIotConnection = "wait_for_iot_connection"
    Fetching = "fetching"
    Configured = "configured"


class Events:
    BackoffExpired = "backoff_expired"
    IotConnection = "iot_connection"
    Received = "received"
    Timeout = "timeout"


def _expire_backoff():
    _event_queue.put({'event': Events.BackoffExpired})


def _connection_callback(connected):
    _event_queue.put({'event': Events.IotConnection, 'connected': connected})


def _event_timeout():
    _event_queue.put({'event': Events.Timeout})


def _handle_backing_off(state, event):
    if event['event'] == Events.BackoffExpired:
        if iot_monitor.is_cloud_connected():
            state.set(States.Fetching)
        else:
            state.set(States.WaitingForIotConnection)


def _handle_wait_for_iot_connection(state, event):
    if event['event'] == Events.IotConnection:
        if event['connected']:
            state.set(States.Fetching)


def _handle_fetching(state, event):
    if event['event'] == Events.Received:
        if event['received_ok']:
            print("Device configured")
            state.set(States.Configured)
            token_sync.received_config()
        else:
            state.set(States.BackingOff)
    elif event['event'] == Events.Timeout:
        state.set(States.BackingOff)


def _handle_configured(state, event):
    if event['event'] == Events.Received:
        if not event['received_ok']:
            print("Device not configured, backing off")
            state.set(States.BackingOff)


def _handle_event(state, event):
    if state.get() == States.BackingOff:
        _handle_backing_off(state, event)
    elif state.get() == States.WaitingForIotConnection:
        _handle_wait_for_iot_connection(state, event)
    elif state.get() == States.Fetching:
        _handle_fetching(state, event)
    elif state.get() == States.Configured:
        _handle_configured(state, event)
    else:
        print(f"State unhandled: {state.get().value}")


async def handle_device_sync(mqtt_conn):
    backoff = BackOff(grow=config.state_initial_backoff, maximum=config.state_maximum_backoff, callback=_expire_backoff)
    timer = Timer(config.state_fetch_timeout, _event_timeout)

    def entry_fetching():
        send_state(mqtt_conn)
        timer.start()

    state = State(
        [States.BackingOff, States.WaitingForIotConnection, States.Fetching, States.Configured], name="device"
    )
    state.set_entry(States.BackingOff, action=backoff.start)
    state.set_exit(States.BackingOff, action=backoff.stop)

    state.set_entry(States.Fetching, action=entry_fetching)

    state.set_entry(States.Configured, action=backoff.reset)

    state.set(States.BackingOff)

    iot_monitor.subscribe(_connection_callback)

    while True:
        try:
            event = await _event_queue.get()
            state.event(event)
            _handle_event(state, event)
            state.finish()
        except asyncio.CancelledError:
            break


def received_config(received=True):
    event = {'event': Events.Received, 'received_ok': received}
    _event_queue.put(event)
