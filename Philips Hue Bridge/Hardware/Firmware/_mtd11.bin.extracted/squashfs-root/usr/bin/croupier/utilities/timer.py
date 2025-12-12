import asyncio


class Timer:
    def __init__(self, interval, callback, once=True, verbose=False):
        self.__interval = interval
        self.__once = once
        self.__callback = callback
        self.__task = None
        self.__verbose = verbose

    async def __run(self):
        while True:
            if self.__verbose:
                print(f"Timer run - sleep for {self.__interval} seconds")
            await asyncio.sleep(self.__interval)

            if self.__callback is not None:
                if self.__verbose:
                    print("Timer run - callback")
                self.__callback()

            if self.__once:
                break

        if self.__verbose:
            print("Timer run complete")
        self.__task = None

    def start(self):
        if self.__verbose:
            print("Timer start")
        if self.__task:
            self.stop()
        self.__task = asyncio.create_task(self.__run())

    def stop(self):
        if self.__verbose:
            print("Timer stop")
        if self.__task:
            self.__task.cancel()
            self.__task = None
