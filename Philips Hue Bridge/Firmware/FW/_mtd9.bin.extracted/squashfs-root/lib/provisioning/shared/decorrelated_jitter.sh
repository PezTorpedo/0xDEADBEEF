#!/usr/bin/env ash
# Copyright (c) 2020 Signify Holding
# shellcheck shell=dash
# shellcheck disable=SC2154

##
# Generates a random backoff based on the previous wait period.
# The newly generated period is between [Base, 3xPreviousWaitPeriod],
# cut off by a maximum value.
# Globals:
#   backoff_base
#   backoff_max
# Arguments:
#   @param Previous Wait Period.
# Outputs:
#   New random wait period is printed to stdout.
#   @return 0 on success.
decorrelated_jitter () {
    local previous=${1}
    local wait_period

    wait_period=$(random_between "${backoff_base}" $(( 3 * previous)) )

    if [ "${wait_period}" -lt "${backoff_max}" ]; then
        valueof "${wait_period}"
    else
        valueof "${backoff_max}"
    fi
}