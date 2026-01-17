#!/usr/bin/env ash
# Copyright (c) 2020 Signify Holding
# shellcheck shell=dash
# shellcheck disable=SC2154

##
# Sends a signed POST request
# Globals: 
#   https_ca_cert_file
#   max_req_time
#   protocol_version
#   key_version
#   sw_version
#   bridge_id
# Arguments:
#   @param url The URL to send the request to
#   @param signature The signature to be used for signing
#   @argument stdin is used as the message body
# Outputs:
#   Writes the received response to stdout
#   @return The curl operation return code.
http_request () {
    # the body comes in stdin

    local url="${1}"
    local signature="${2}"
    local curl_result

    # include headers and avoid printing the progress bar
    curl_result="$(curl "${url}" \
            --include \
            --silent \
            --cacert "${https_ca_cert_file}" \
            --max-time "${max_req_time}" \
            --request POST \
            --header "Content-Type: application/json" \
            --header "protocol-version: ${protocol_version}" \
            --header "key-version: ${key_version}" \
            --header "sw-version: ${sw_version}" \
            --header "Device-Id: ${bridge_id}" \
            --header "Signature: ${signature}" \
            --header "alg: HS256" \
            --data-binary @-)"
    local curl_return_code=$?
    valueof "${curl_result}" | sed 's/\r//'
    return ${curl_return_code}
}

##
# Extracts the status code from an HTTP response.
# Arguments:
#   The response is extracted from stdin.
# Outputs:
#   Status code is printed to stdout.
#   @return 0 on success.
http_separate_status () {
    head -1 | sed -E 's|^HTTP/[^ ]+ ([0-9]+) .*$|\1|' # only capture the status
}

##
# Extracts the specificed header field from the HTTP response.
# Arguments:
#   @param Header field name.
#   HTTP response is extracted from stdin.
# Outputs:
#   The header field data is printed to stdout with the header name.
#   @return 0 on success.
http_get_header_value () {
    sed -E -n "s|^${1}: (.*)|\1|pI" # only print the value in a line that starts with the header name
}

##
# Extracts the body of an HTTP response.
# Arguments:
#   The response is extracted from stdin.
# Outputs:
#   The body of the response is printed to stdout.
#   @return 0 on success.
http_get_body () {
   sed -e '1,/^$/ d' # skip everything until first empty line, capture what follows
}

##
# Checks whether the status is 200: OK.
# Arguments:
#   @param HTTP status code.
# Outputs:
#   @return Check result of status being 200.
http_is_ok () {
    [ "${1}" = "200" ]
}
