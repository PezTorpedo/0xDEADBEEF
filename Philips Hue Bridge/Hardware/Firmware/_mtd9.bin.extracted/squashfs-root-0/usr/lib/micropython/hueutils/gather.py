# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

import asyncio

# this offers an alternative to the gather function implemented in micropython 1.14

# the original function does not behave as the cpython's one. Exceptions raised by tasks other
# than the first one will not be propagated to the caller


# this function also diverges from the canonical implementation as it DOES cancel all awaitables
async def gather_ex(*aws, return_exceptions=False):
    exit_event = asyncio.Event()
    msgs = []

    async def wrap_task(aw, idx):
        try:
            msgs.append((idx, await aw))
        except Exception as e:
            msgs.append((idx, e))
        finally:
            exit_event.set()
            exit_event.clear()

    def cancel_remaining_tasks(tasks_):
        for el in tasks_:
            if el:
                el.cancel()

    tasks = [
        asyncio.core._promote_to_task(wrap_task(aws[i], i)) for i in range(len(aws))  # pylint: disable=protected-access
    ]

    collected = 0

    results = [None] * len(tasks)

    while collected < len(tasks):
        await exit_event.wait()
        for idx, result in msgs:
            if not return_exceptions and isinstance(result, Exception):
                cancel_remaining_tasks(tasks)
                raise result
            results[idx] = result
            collected += 1
            tasks[idx] = None

    return results
