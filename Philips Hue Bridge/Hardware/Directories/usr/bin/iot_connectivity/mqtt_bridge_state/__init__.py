import time

_current_state = None  # guarantee a state change at start time


# report changes in the state of the bridge connection
# only sends messages on transitions
async def track_bridge_state(mqtt, *report_queues):
    global _current_state

    async for msg in mqtt.subscribe("$SYS/broker/connection/cloud/state"):
        state = msg["payload"].decode() == "1"
        if state != _current_state:
            now = time.ticks_ms()
            payload = (now, state)
            for q in report_queues:
                q.put(payload)
        _current_state = state
