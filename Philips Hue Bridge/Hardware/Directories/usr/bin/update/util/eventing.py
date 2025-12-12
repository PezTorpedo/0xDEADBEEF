# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

from asyncio import Event

from util.persistence import DataObject


class AsynchronousEvent(DataObject):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.__event = Event()

    def __str__(self):
        return f"{type(self).__name__}(accepted={self.__event.is_set()}, fields={str(self.__dict__)})"

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return self.accept()

    def accept(self, **kwargs):
        self.update(**kwargs)
        self.__event.set()

    async def wait_accepted(self):
        await self.__event.wait()
