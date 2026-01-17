#!/usr/bin/env ash
# Copyright (c) 2020 Signify Holding
# shellcheck shell=dash

##
# Calculates the HMAC SHA-256 signature given the key.
# Arguments:
#   @param Key value in hex.
#   Body to be signed is given by stdin.
# Outputs:
#   Signature is printed to stdout.
#   @return 0 on success.
hmac_sha256 () {
    openssl dgst -sha256 -mac HMAC -macopt "hexkey:${1}" | cut -d' ' -f2
}

##
# Calculates the HMAC SHA-256 signature and converts it to Bse64 encoding.
# Arguments:
#   @param Key value in hex.
#   Body to be signed is given by stdin.
# Outputs:
#   Signature is printed in Base64 encoding to stdout.
#   @return 0 on success.
hmac_sha256_base64 () {
    openssl dgst -sha256 -binary -mac HMAC -macopt "hexkey:${1}" | base64_encode
}
