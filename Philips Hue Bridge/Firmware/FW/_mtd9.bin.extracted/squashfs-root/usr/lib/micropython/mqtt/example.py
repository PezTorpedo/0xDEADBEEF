# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

import uasyncio as asyncio

from mqtt import Mqtt


async def test_producer(m):
    while True:
        await asyncio.sleep(1)
        m.publish("test", "hey")


async def echo_producer(m):
    while True:
        await asyncio.sleep(2)
        m.publish("echo", "it works")


async def test_handler(mqtt):
    async for msg in mqtt.subscribe("test"):
        print(msg)


async def echo_handler(mqtt):
    async for msg in mqtt.subscribe("echo"):
        print(msg)


async def main():
    async with Mqtt("pymosquitto", "user", "pwd") as m:
        tasks = []
        tasks.append(asyncio.create_task(test_producer(m)))
        tasks.append(asyncio.create_task(echo_producer(m)))
        tasks.append(asyncio.create_task(test_handler(m)))
        tasks.append(asyncio.create_task(echo_handler(m)))

        await asyncio.gather(*tasks)


asyncio.run(main())
asyncio.get_event_loop().run_forever()
