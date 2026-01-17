#!/usr/bin/env ash
# Copyright (c) 2020 Signify Holding
# shellcheck shell=dash

##
# Checks for NTP time.
# Outputs:
#   Prints the network time status to stdout.
check_for_network_time () {
    grep -q -m 1 -E "ntpd|tlsdate" /tmp/ntpd/sync
}
