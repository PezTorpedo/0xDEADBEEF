#!/usr/bin/env ash
# Copyright (c) 2020 Signify Holding
# shellcheck shell=dash

##
# Encodes the input in Base64.
# Arguments:
#   The input is extracted from stdin.
# Outputs:
#   The Base64 output is printed to stdout.
#   @return 0 on success.
base64_encode () {
    openssl base64 -A
}

##
# Converts a hex string to a binary.
# Arguments:
#   The input is extracted from stdin.
# Outputs:
#   The binary output is printed to stdout.
#   @return 0 on success.
hex_to_bin () {
    sed -e 's/../\\x&/g' | xargs -0 printf "%b"
}

##
# Converts a binary string to hex.
# Arguments:
#   The input is extracted from stdin.
# Outputs:
#   The hex output is printed to stdout.
#   @return 0 on success.
bin_to_hex () {
    hexdump -v -e '/1 "%02x"'
}
