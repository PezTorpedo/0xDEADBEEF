# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

import os
from asyncio import Event, TimeoutError, wait_for, wait_for_ms
from random import getrandbits

__ENTROPY_BITS = 16


def unlink_quietly(file_path: str):
    try:
        os.unlink(file_path)
    except Exception:
        pass


def simple_read(path: str) -> str:
    with open(path) as file:
        return file.readline().rstrip("\n")


def simple_write(path: str, data) -> str:  # NOQA
    with open(path, "w") as file:
        file.write(data)


def curry(func, *extra_args):  # NOQA
    def curried(*args):
        return func(*extra_args, *args)

    return curried


async def wait_ex(event: Event, timeout: float) -> bool:
    try:
        await wait_for(event.wait(), timeout)
        return False
    except TimeoutError:
        return True


async def wait_ex_ms(event: Event, timeout: int) -> bool:
    try:
        await wait_for_ms(event.wait(), timeout)
        return False
    except TimeoutError:
        return True


def random_interval(interval_s: int) -> float:
    return interval_s * getrandbits(__ENTROPY_BITS) / (2**__ENTROPY_BITS - 1)


def random_window(window_s: int) -> float:
    return window_s / 2 - random_interval(window_s)


def pretty_interval(interval_s: float) -> str:
    remainder_s = interval_s
    hours = interval_s // (60 * 60)
    remainder_s -= hours * 60 * 60
    minutes = remainder_s // 60
    remainder_s -= minutes * 60
    if hours:
        return f"{plu(int(hours), 'hour')} {plu(int(minutes), 'minute')} {remainder_s:0.2f} seconds"
    if minutes:
        return f"{plu(int(minutes), 'minute')} {remainder_s:0.2f} seconds"
    return f"{remainder_s:0.2f} seconds"


def plu(count: int, noun: str) -> str:
    return f"{count} {noun}{'' if count == 1 else 's'}"


def gt(constant):
    def inner(value):
        return value > constant

    return inner


def neq(constant):  # NOQA
    def inner(value):
        return value != constant

    return inner


def match(*types, **conditions):
    """
    Returns a tailor-made predicate that will match the type and
    propertieds of an object instance.

    Example usage:
    ```python
    predicate = match(Bumblebee, mood="happy")
    ```

    The resulting predicate would evaluate to `True` for all instances
    of `class Bumblebee`, that either have a public property `mood` equal to "happy",
    or a public method `mood()` returning "happy".

    The expected value can be a tuple, in which case `in` will be used
    instead of `==` internally in order to check if the argument matches
    the expected value.

    Multiple argument-value pairs can be given, as well as multiple expected
    types.

    Another example:
    ```python
    predicate = match(Bumblebee, Wasp, mood=("happy", "grumpy"), in_flight=True)
    ```

    And finally, the expected value can be a predicate as well, which will
    be evaluated on the argument.

    Yet another example:
    ```python
    predicate = match(Bumblebee, in_flight=True, speed_m_s=gt(100))
    ```

    In this example, `gt(100)` curries a comparison function of two
    arguments to create a binary predicate of one argument.
    """

    def check(argument, value):
        if isinstance(value, tuple):
            return argument in value
        elif type(value).__name__ in ("function", "closure"):
            return value(argument)
        return argument == value

    def inner(object):
        if isinstance(object, types):
            for key, value in conditions.items():
                member = getattr(object, key)
                if type(member).__name__ == "bound_method":
                    if not check(member(), value):
                        return False
                elif not check(member, value):
                    return False
            return True
        return False

    return inner


def memoize(func):
    memoized_values = {}

    def wrapper(*args):
        if args not in memoized_values:
            memoized_values[args] = func(*args)
        return memoized_values[args]

    return wrapper
