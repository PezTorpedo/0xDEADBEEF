import asyncio
import sys


class BackOff:
    def __init__(self, grow=2, maximum=None, callback=None, verbose=False):
        self.__verbose = verbose
        self.__initial = 0
        self.__grow = grow
        self.__next = grow
        self.__max = maximum if maximum is not None else sys.maxint
        self.__interval = 0
        self.__callback = callback
        self.__task = None

    def reset(self):
        if self.__verbose:
            print("BackOff: reset")
        self.stop()
        self.__interval = self.__initial
        self.__next = self.__grow

    def start(self):
        if self.__verbose:
            print("BackOff: start")
        if self.__task is None:
            self.__task = asyncio.create_task(self.__run())

    def stop(self):
        if self.__verbose:
            print("BackOff: stop")
        if self.__task is not None:
            self.__task.cancel()
            self.__task = None

    async def __run(self):
        if self.__verbose:
            print(f"BackOff: interval:{self.__interval}, grow:{self.__next}, max:{self.__max}")
        while True:
            await asyncio.sleep(self.__interval)
            old_interval = self.__interval
            if self.__callback is not None:
                self.__callback()
            # Improve the algorithm with randomness
            self.__interval = min(self.__interval + self.__next, self.__max)
            self.__next *= 2
            if self.__verbose:
                print(f"BackOff: expired:{old_interval}, next:{self.__next}")
