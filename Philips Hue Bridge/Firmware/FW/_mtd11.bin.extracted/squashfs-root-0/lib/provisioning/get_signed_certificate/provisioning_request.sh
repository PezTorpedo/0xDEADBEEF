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
    now_value=$(date "+%s")
    printf "%s" "${now_value}"
}

##
# Generates a Signing Request JSON data.
# Globals:
#   device_name
#   cert_type
# Arguments:
#   @param Token to be used.
#   @param Reason for the request.
#   @param The CSR.
# Outputs:
#   Prints the signing request JSON to stdout
#   @return 0 on success.
_generate_signing_request () {
    local device_id="${1}"
    local reason="${2}"
    local csr="${3}"
    local now_value
    now_value=$(_get_now)

    printf '{"timestamp":%d,"deviceid":"%s","devicetype":"%s","certtype":"%s","reason":"%s","csr":"%s","sw-version":"%s"}' \
        "${now_value}" "${device_id}" "${device_name}" "${cert_type}" "${reason}" "${csr}" "${sw_version}"
}

##
# Sends a signing request to the server.
# Globals:
#   bridge_id
#   signingKey_B2PE
#   server_url
# Arguments:
#   @param reason The reason for the request.
#   @param csr Generated csr string.
# Outputs:
#   Signature result is printed to stdout
#   @return Exit code of the Curl command
request_signature () {
    local reason="${1}"
    local csr="${2}"

    local req
    local signature
    local http_result
    local http_exit_code
    local url="${server_url}/v3/cert"

    req="$(_generate_signing_request "${bridge_id}" "${reason}" "${csr}")"
    signature="$(valueof "${req}" | hmac_sha256_base64 "${signingKey_B2PE}")"

    http_result="$(valueof "${req}" | http_request "${url}" "${signature}")"
    http_exit_code=$?
    valueof "${http_result}"
    return ${http_exit_code}
}
