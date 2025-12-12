#!/bin/sh

# this library is mostly a wrapper around jshn
# to use it, you must source jshn before sourcing this file
#
# NOTE: because this code uses jshn, no other use of jshn can happen concurrently

DIAG_MQTT_TOPIC="diagnostics"

diag_init () {
    DIAG_HOST="${1}"
    DIAG_COMPONENT="${2}"
    DIAG_USERID_PREFIX="diag_${DIAG_COMPONENT}"
}

diag_new_report () {
    json_init
    json_add_double "timestamp" "$(_diag_get_current_time).0"
    json_add_string "component" "${DIAG_COMPONENT}"
}

diag_set_report_type () {
    json_add_string "type" "${1}"
}

diag_set_report_subtype () {
    json_add_string "subType" "${1}"
}

diag_set_report_category () {
    json_add_string "category" "${1}"
}

diag_begin_report_body () {
    json_add_object "body"
}

diag_end_report_body () {
    json_close_object
}

diag_add_string () {
    json_add_string "$@"
}

diag_add_int () {
    json_add_int "$@"
}

diag_add_boolean () {
    json_add_boolean "$@"
}

diag_add_double () {
    json_add_double "$@"
}

diag_add_null () {
    json_add_null "$@"
}

diag_add_object () {
    json_add_object "$@"
}

diag_close_object () {
    json_close_object "$@"
}

diag_add_array () {
    json_add_array "$@"
}

diag_close_array () {
    json_close_array "$@"
}

diag_publish_report () {
    _diag_run_in_background _diag_send "$(json_dump)" "${1}"
}

_diag_get_current_time () {
    date -u "+%s"
}

_diag_run_in_background () {
    ("$@" &)&
}

_diag_pub_over_posix_queue () {
    mqueue_pub -t "${DIAG_MQTT_TOPIC}/${2}" -m "${1}"
}

_diag_send () {
    while : ; do
        if _diag_pub_over_posix_queue "${1}" "${2}"; then
            break
        fi
        sleep 1
    done

}