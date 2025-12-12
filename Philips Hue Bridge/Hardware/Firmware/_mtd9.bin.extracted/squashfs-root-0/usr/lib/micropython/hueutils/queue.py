# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

import asyncio

# needed as micropython does not provide it. Implementation based on CPython's API


class Queue:
    def __init__(self):
        self._ev = asyncio.Event()
        self._queue = []

    async def get(self):
        if self._queue:
            return self._queue.pop(0)

        await self._ev.wait()
        return self._queue.pop(0)

    def put(self, msg):
        self._queue.append(msg)
        self._ev.set()
        self._ev.clear()
