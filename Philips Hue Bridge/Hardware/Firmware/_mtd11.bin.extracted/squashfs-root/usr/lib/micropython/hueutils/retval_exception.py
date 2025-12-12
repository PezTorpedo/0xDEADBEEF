# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Callable
else:
    Callable = object


def _return_must_satisfy(condition_check: Callable, func, args, error_type):
    ret = func(*args)
    if condition_check(ret):
        return ret
    raise error_type


def must_not_return(val, func: Callable, error_type=AssertionError):
    def wrapper(*args):
        return _return_must_satisfy(lambda x: x is not val, func, args, error_type)

    return wrapper


def must_return(val, func: Callable, error_type=AssertionError):
    def wrapper(*args):
        return _return_must_satisfy(lambda x: x is val, func, args, error_type)

    return wrapper
