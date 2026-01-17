# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

import time

import config


def calculate_report_period_offset(eui64: str) -> int:
    entropy = int(eui64, 16) & 0xFFFF if eui64 else 0
    return (entropy * config.report_period) // 65535


def calculate_next_report_time(resync=False) -> int:
    now = time.time()
    period = config.report_period

    if not resync:
        return time.ticks_add(time.ticks_ms(), int(period * 1000))

    begin_of_report_interval = (now // period) * period
    schedule = begin_of_report_interval + config.fixed["report_period_offset"]
    if schedule < now:
        # Did we miss the scheduled time? Then defer until the next period.
        schedule += period

    # We need to be careful when converting timestamps to ticks, as the
    # delta between then is not constant due to ticks wrap-around.
    return time.ticks_add(time.ticks_ms(), int((schedule - now) * 1000))
