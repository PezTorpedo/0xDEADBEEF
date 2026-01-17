#!/usr/bin/env ash
# Copyright (c) 2020 Signify Holding
# shellcheck shell=dash
# shellcheck disable=SC2154

##
# Returns the current date/time.
# Outputs:
#   Prints the current date/time to stdout.
_get_now () {
    local now_value
    now_value="$(date "+%s")"
    printf "%s" "${now_value}"
}

##
# Checks whether the Certificate Directory exists.
# Globals:
#   certificate_directory
# Outputs:
#   @return Existence of Certificate Directory.
_does_cert_directory_exists () {
    [ -d "${certificate_directory}" ]
}

##
# Checks the checksums file for existence and validity.
# Globals:
#   certificate_directory
#   checksums_file
# Outputs:
#   @return 0 if file exists and is valid.
_are_all_files_in_place () {
    (
        cd "${certificate_directory}" || return 1
        if [ ! -f "${checksums_file}" ]; then
            return 1
        fi

        sed 's/  /\t/' "${checksums_file}" |  cut -f2 | xargs find > /dev/null 2> /dev/null
    )
}

##
# Checks the Checksums in the file.
# Globals:
#   certificate_directory
#   checksums_file
# Outputs:
#   @return 0 if checksums match.
_do_checksums_match () {
    (
        cd "${certificate_directory}" || return 1
        sha1sum -c "${checksums_file}" > /dev/null 2> /dev/null
    )
}

##
# Reads the certificate date from the certificate file.
# The requested type of certificate is extracted from the file.
# Its content is parsed to get the date and formated into UTC.
# Globals:
#   certificate_file
# Arguments:
#   @param Information Type requested.
# Outputs:
#   Prints the certificate date to stdout.
#   @return Returns 0 on success.
_read_cert_date () {
    local cert_time_openssl
    local cert_time_reformat
    local type="${1}"

    cert_time_openssl=$(openssl x509 -noout "-${type}" -in "${certificate_file}" | cut -d'=' -f2)
    cert_time_reformat=$(date -d "${cert_time_openssl}" -D "%b %d %T %Y" +'%Y-%m-%d %H:%M:%S')

    date -u "+%s" -d "${cert_time_reformat}"
}

##
# Requests the Creation Date of the certificate.
# Outputs:
#   Prints the certificate start date to stdout.
#   @return Returns 0 on success.
_read_creation_date () {
    _read_cert_date "startdate"
}

##
# Requests the Expiration Date of the certificate.
# Outputs:
#   Prints the certificate end date to stdout.
#   @return Returns 0 on success.
_read_expiration_date () {
    _read_cert_date "enddate"
}

##
# Checks whether the certificate is expired.
# Outputs:
#   @return Expiration: Now >= Expiration Date.
_is_certificate_expired () {
    local expiration
    local current_time
    expiration=$(_read_expiration_date)
    current_time=$(_get_now)
    [ "${current_time}" -ge "${expiration}" ]
}

##
# Checks whether the certificate is close to expiration.
# This is done by comparing the life-span of the certificate with
# the custom renew_window setting: Expiration Date - Renewal Window.
# Globals:
#   renew_window: A Percentage value.
# Outputs:
#   @return Close to Expiration: Now >= ( Expiration - Lifespan x Renewal % ).
_is_certificate_close_to_expire () {
    local expiration
    local current_time
    expiration=$(_read_expiration_date)
    current_time=$(_get_now)
    local lifespan=$(( expiration - $(_read_creation_date) ))
    local renew_start=$(( (100 * expiration - lifespan * renew_window) / 100 ))

    [ "${current_time}" -ge "${renew_start}" ]
}

##
# Investigates the certificate state and prints it
# Outputs:
#   Certificate state is printed to stdout.
get_certificate_state () {
    if ! _does_cert_directory_exists; then
        echo "factory_reset"
        return
    fi

    if ! _are_all_files_in_place; then
        echo "missing_files"
        return
    fi

    if ! _do_checksums_match; then
        echo "corrupted_files"
        return
    fi

    if _is_certificate_expired; then
        echo "expired_certificate"
        return
    fi

    if _is_certificate_close_to_expire; then
        echo "close_to_expiration"
        return
    fi

    echo "healthy_certificate"
}

##
# Converts the Certificate State to Request Reason.
# The return code can be used to check whether a request is needed.
# The request reason is printed to stdout, to be used within the request.
# Outputs:
#   Prints the request reason to stdout.
#   @return Returns 0 for healthy certificate, 1 otherwise.
translate_reason () {
    case "${1}" in
        "factory_reset" | "missing_files" | "corrupted_files" | "expired_certificate" )
            echo enroll
            return 1
            ;;
        "close_to_expiration")
            echo renewal
            return 1
            ;;
        "healthy_certificate")
            echo nothing
            return 0
            ;;
        *)
            echo enroll
            return 1
            ;;
    esac
}

##
# Updates the checksums with the new file contents.
# Globals:
#   certificate_directory
#   checksums_file
# Outputs:
#   @return 0 on success.
certificate_state_update_checksums () {
    (
        cd "${certificate_directory}" || return 1
        sha1sum ./* > "${checksums_file}"
    )
}
