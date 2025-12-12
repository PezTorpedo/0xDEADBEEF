#!/usr/bin/env ash
# Copyright (c) 2020 Signify Holding
# shellcheck shell=dash

##
# Prints a 32-bit unsigned random variable.
# Outputs:
#   Prints a 4 byte unsigned random value to stdout.
#   @return 0 on success.
_random_32_bits () {
    hexdump -e '1/4 "%u"' -n 4 /dev/urandom
}

##
# Generates a random variable betwee the given ranges.
# Arguments:
#   @param min Lower bound of the range.
#   @param max Upper bound of the range.
# Outputs:
#   Prints the random value to stdout.
#   @return 0 if successful.
random_between () {
    local min=${1}
    local max=${2}
    local range=$((max - min))
    local rand
    rand=$(_random_32_bits)
    valueof $(( min + (rand * range) / 4294967296 ))
}
