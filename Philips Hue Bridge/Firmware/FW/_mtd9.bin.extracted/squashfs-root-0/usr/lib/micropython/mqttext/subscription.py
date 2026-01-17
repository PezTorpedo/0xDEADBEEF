from hueutils.queue import Queue


class Subscription:
    def __init__(self, mqtt: int, subscription: str, qos: int):
        self.mqtt = mqtt
        self.qos = qos
        self.sub = subscription

    def __aiter__(self):
        self._ev = Queue()
        return self

    async def __anext__(self):
        return await self._ev.get()

    def send(self, msg):
        self._ev.put(msg)
