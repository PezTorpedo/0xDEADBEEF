#!/bin/ash
# Copyright (c) 2025 Signify Holding

source /usr/share/determine_swversion.sh
source /usr/share/libubox/jshn.sh # needed for diag_report
source /lib/shell-diagnostics/diag_report.sh

# This must be called from the script that uses it
datastore_backup_restore_init() {
    EXITCODE=0
    DATASTORE_BACKUP_RESTORE_COMPONENT="${1}"
    diag_init localhost "${DATASTORE_BACKUP_RESTORE_COMPONENT}"
}

##
# Sends a diagnostic event.
# Arguments:
#   @param Process name.
#   @param exit code.
#   @param execution time.
# Outputs:
#   @return 0 on success.
send_diagnostics_event () {
    diag_new_report

    diag_set_report_category "diagnostics"
    diag_set_report_type "migration_events"

    diag_begin_report_body
        diag_add_string "action_type" "${DATASTORE_BACKUP_RESTORE_COMPONENT}"
        diag_add_string "process" "${1}"
        diag_add_string "exit_code" "${2}"
        diag_add_string "exec_time" "${3}"
    diag_end_report_body

    diag_publish_report "migration_events"
}

log () {
    logger -s -t "${DATASTORE_BACKUP_RESTORE_COMPONENT}" "$@"
}

run_process() {
    local start_time=$(date +%s)
    timeout 60s "$@"
    local exit_code=$?
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    if [ ${exit_code} -ne 0 ]; then
        log "$* failed!"
        EXITCODE=1
    fi

    local process_name=${1}

    send_diagnostics_event ${process_name} ${exit_code} ${duration}
}

formatArgFromUbootEnvVar() {
    local OPTION=$1;shift
    local KEY=$1;shift
    local VALUE=$(fw_printenv -n ${KEY} 2>/dev/null)
    if [ -n "${VALUE}" ]; then
        echo -n " ${OPTION} ${VALUE}"
    fi
}
