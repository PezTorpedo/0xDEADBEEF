#!/usr/bin/env ash
# Copyright (c) 2020 Signify Holding
# shellcheck shell=dash
# shellcheck disable=SC2154

##
# Obtains the certificate and authenticates its signature.
# The certificate is stored into the file and checksums are updated.
# If any step fails, exit code is updated and a diagnostic event is sent.
# Globals:
#   error_unknown
#   error_args
#   error_curl
#   error_signature
#   error_http_error
#   error_ok
#   certificate_reason
#   certificate_file
#   service_file
# Arguments:
#   @param Certificate reason.
#   @param Certificate directory.
# Outputs:
#   @return See error_list.sh for error codes.
main () {
    exit_status=${error_unknown}

    if ! process_cmd_arguments "$@"; then
        exit_with "${error_args}"
    fi

    init_globals

    set_exit_on_errors
    set_exit_trap on_exit

    set_ctn_dependent_variables
    check_exit_code_and_report_it_and_exit "error_get_certificate" "Set Ctn Failed"
    diag_init localhost provisioning

    load_signing_keys
    check_exit_code_and_report_it_and_exit "error_get_certificate" "Load Signing Keys Failed"
    create_private_key
    check_exit_code_and_report_it_and_exit "error_get_certificate" "Create Private Key Failed"

    local csr
    local result
    local http_status_code
    local req_exit_code
    local pubsub_url

    csr="$(create_csr)"
    check_exit_code_and_report_it_and_exit "error_get_certificate" "Create CRS Failed"

    # Separate the signature http request from the trap to get curl error.
    clear_exit_on_errors

    result="$(request_signature "${certificate_reason}" "${csr}")"
    req_exit_code=$?

    if [ "${req_exit_code}" -ne "0" ]; then
        log_message "curl error (${req_exit_code})"
        send_diagnostics_event "error_curl" "curl exited with ${req_exit_code}" "${provisioning_reason}"
        exit_with "${error_curl}"
    fi

    # Restart the trap for any error change.
    set_exit_on_errors
    set_exit_trap on_exit

    http_status_code=$(valueof "${result}" | http_separate_status)
    check_exit_code_and_report_it_and_exit "error_get_certificate" "Separate Status Failed"

    if http_is_ok "${http_status_code}"; then
        local result_body
        local signature
        result_body="$(valueof "${result}" | http_get_body)"
        check_exit_code_and_report_it_and_exit "error_get_certificate" "Get Body Failed"

        signature=$(valueof "${result}" | http_get_header_value "Signature")
        check_exit_code_and_report_it_and_exit "error_get_certificate" "Get Signature Header Failed"

        if check_response_signature "${result_body}" "${signature}"; then
            extract_certificate_from_response "${result_body}" > "${certificate_file}"
            check_exit_code_and_report_it_and_exit "error_get_certificate" "Extract Certificate Failed"

            extract_service_details_from_response "${result_body}" > "${service_file}"
            check_exit_code_and_report_it_and_exit "error_get_certificate" "Extract Service Details Failed"

            certificate_state_update_checksums
            check_exit_code_and_report_it_and_exit "error_get_certificate" "Update Checksums Failed"

            # The URL extraction has to be done only when other extraction is successful.
            pubsub_url=$(extract_server_url_from_response "${result_body}")

            log_message "provisioning data received and stored. url: ${pubsub_url}"
        else
            log_message "signature does not match"
            send_diagnostics_event "error_signature" "" "${provisioning_reason}"
            exit_with "${error_signature}"
        fi
    else
        log_message "HTTP request error ${http_status_code}"
        send_diagnostics_event "error_http" "HTTP error ${http_status_code}" "${provisioning_reason}"
        exit_with "${error_http_error}"
    fi

    sync

    send_diagnostics_event "done" "provisioned url : ${pubsub_url}" "${provisioning_reason}"

    exit_with "${error_ok}"
}

##
# Trap to be called on exit, sends a diagnostic if an unknown error occurs.
# Globals:
#   exit_status
#   error_unknown
# Outputs:
#   @return Exit code is the error that caused this trap to be called.
on_exit () {
    clear_exit_on_errors

    if [ "${exit_status}" = "${error_unknown}" ]; then
        send_diagnostics_event "error_unknown" "" "${provisioning_reason}"
    fi

    exit "${exit_status}"
}
