#!/usr/bin/env ash
# Copyright (c) 2020 Signify Holding
# shellcheck shell=dash
# shellcheck disable=SC2034

# No Error
readonly error_ok=0

# Argument count error
readonly error_args=1

# Erroneous or Expired certificate
readonly error_state=2

# Curl Command Failed
readonly error_curl=3

# HTTP Response in not 200
readonly error_http_error=4

# HTTP Response Signature failed
readonly error_signature=5

# Invalid CTN or CTN not found in UBoot
readonly error_no_ctn=6

# Unknown error
readonly error_unknown=255

translate_error_code_to_text () {
    case $1 in
        0) echo "ok";;
        1) echo "arguments";;
        2) echo "state";;
        3) echo "curl";;
        4) echo "http";;
        5) echo "signature";;
        6) echo "ctn";;
        *) echo "unknown";;
    esac
}