#!/usr/bin/env ash
# Copyright (c) 2020 Signify Holding
# shellcheck shell=dash


##
# Creates the keys for signing.
# Arguments:
#   @param Length of the key.
#   @param Input key string.
#   @param Salt for key generation.
#   @param Key information.
# Outputs:
#   Prints the key pair to stdout.
#   @return 0 on success.
hkdf () {
    local length="${1}"
    local input_key_material="${2}"
    local salt="${3}"
    local info="${4}"

    local hash_len=32

    if [ "${salt}" = "" ]; then
        salt=$( print_repeated_string '0' $((hash_len * 2)) ) # times 2 because we're using hex
    fi

    local rounds

    local Ki
    local hex_info
    local okm=""
    local t=""

    rounds=$(ceil_div "${length}" "${hash_len}")
    Ki=$(valueof "${input_key_material}" | hex_to_bin | hmac_sha256 "${salt}")
    hex_info=$(valueof "${info}" | bin_to_hex)

    for i in $(seq 1 "${rounds}"); do
        t=$(printf "%s%s%02x" "${t}" "${hex_info}" "${i}" | hex_to_bin | hmac_sha256 "${Ki}")
        okm="${okm}${t}"
    done

    valueof "${okm}" | cut -c1-$((2*length))
}
