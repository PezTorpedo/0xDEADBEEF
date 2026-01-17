#!/usr/bin/env ash
# Copyright (c) 2020 Signify Holding
# shellcheck shell=dash
# shellcheck disable=SC2154
# shellcheck disable=SC1090,SC1091 # don't even try to lint it
. "${ROOT}"/usr/share/libubox/jshn.sh
# shellcheck disable=SC1090,SC1091 # linted somewhere else
. "${ROOT}"/lib/shell-diagnostics/diag_report.sh

##
# Sends a diagnostic event.
# Globals:
#   cert_type
# Arguments:
#   @param Event Name.
#   @param Event description.
#   @param Reason to provision.
# Outputs:
#   @return 0 on success.
send_diagnostics_event () {
    diag_new_report

    diag_set_report_category "diagnostics"
    diag_set_report_type "cert_provisioning_events"

    diag_begin_report_body
        diag_add_string "cert_type" "${cert_type}"
        diag_add_string "event" "${1}"
        diag_add_string "description" "${2}"
        diag_add_string "provisioning_reason" "${3}" 
    diag_end_report_body

    diag_publish_report "cert_provisioning_events"
    # The last provisioning error needs to be sent as retained message
    # for IoT connect status report
    # FIXME: in some cases, the description is a full json string, so we need to escape it
    escaped_json_description=''
    last_error="{\"event\": \"${1}\",\"description\": \"${escaped_json_description}\"}"
    mosquitto_pub -t 'report/provisioning' -r -m "{\"last_provisioning_event\":$last_error}"
}

##
# Checks the last exit code and reports a diagnostic if it failed
# Arguments:
#   @param Event name to be reported under failure
#   @param Event description to be reported under failure
#   @param Return code of the previous statement
# Outputs:
#   @return Forwards the previous return code.
check_exit_code_and_report_it () {
    local previous_exit_code=${?}
    local event_name="${1}"
    local event_description="${2}"

    local combined_description="Exit code ${previous_exit_code} - ${event_description}"
    if [ "${previous_exit_code}" -ne "0" ]; then
        send_diagnostics_event "${event_name}" "${combined_description}"
    fi
    return ${previous_exit_code}
}

##
# Checks the last exit code and reports a diagnostic if it failed and exits the script
# Arguments:
#   @param Event name to be reported under failure
#   @param Event description to be reported under failure
#   @param Return code of the previous statement
# Outputs:
#   @return Forwards the previous return code.
check_exit_code_and_report_it_and_exit () {
    local previous_exit_code=${?}
    local event_name="${1}"
    local event_description="${2}"
    local combined_description="Exit code ${previous_exit_code} - ${event_description}"
    if [ "${previous_exit_code}" -ne "0" ]; then
        send_diagnostics_event "${event_name}" "${combined_description}"
        log_message "${event_name} : ${combined_description}"
        exit ${previous_exit_code}
    fi
}
