#!/usr/bin/env ash
# Copyright (c) 2023 Signify Holding
# shellcheck shell=dash
# shellcheck disable=SC2154

##
# Publishes provisioning status.
# Arguments:
#   @param status.
# Outputs:
#   Publishes the provisioning status on retained topic.
#   @return 0 on success.
publish_provisioning_status () {
    local status="${1}"
    mosquitto_pub -r -t "${topic_prov_status}" -m "${status}"
}