#!/usr/bin/env ash
# Copyright (c) 2020 Signify Holding
# shellcheck shell=dash
# shellcheck disable=SC2154

##
# Authenticates the reported signature.
# Globals:
#   signingKey_PE2B
# Arguments:
#   @param Body of the message to be authenticated.
#   @param Reported signature for the body.
# Outputs:
#   @return Signature check result.
check_response_signature () {
    local body="${1}"
    local reported_signature="${2}"

    local calculated_signature

    calculated_signature="$(valueof "${body}" | hmac_sha256_base64 "${signingKey_PE2B}")"

    [ "${reported_signature}" = "${calculated_signature}" ]
}

##
# Extracts the certificate portion from the body.
# Arguments:
#   @param Body of the authenticated message.
# Outputs:
#   Certificate information is printed to stdout.
#   @return 0 on success.
extract_certificate_from_response () {
    jsonfilter -s "${1}" -e '@["cert"]'
}

##
# Extracts the service details portion from the body.
# Arguments:
#   @param Body of the authenticated message.
# Outputs:
#   Service details are printed to stdout.
#   @return 0 on success.
extract_service_details_from_response () {
    jsonfilter -s "${1}" -e '@["configs"].connection_params'
}

##
# Extracts the url portion from the body.
# Arguments:
#   @param Body of the authenticated message.
# Outputs:
#   @return url.
extract_server_url_from_response () {
    url=$(jsonfilter -s "${1}" -e '@["configs"].connection_params.url')
    echo "${url}"
}