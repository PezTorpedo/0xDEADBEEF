#!/usr/bin/env ash
# Copyright (c) 2020 Signify Holding
# shellcheck shell=dash

ceil_div () {
    echo -n $(( (${1} + ${2} - 1) / ${2} ))
}

##
# Prints the current uptime in miliseconds
# Outputs:
#   Prints the current uptime in ms to stdout
#   @return 0 on success.
current_uptime () {
    local fraction_time
    fraction_time=$(cut -f1 -d' ' /proc/uptime | tr -d '.') # convert first column to 1/100th of second
    fraction_time="${fraction_time}0" # append a 0 to convert to ms
    echo "${fraction_time}"
}

##
# Prints the value of given parameters
# Arguments:
#   Any argument to be printed
# Outputs:
#   The value of the argument is printed to stdout
#   @return 0 if printing is successful
valueof () {
    printf "%s" "$@"
}

##
# Prints a string repeatedly.
# Arguments:
#   @param String to be repeated.
#   @param Number of times to be repeated.
# Outputs:
#   Prints the repeated string to stdout.
#   @return 0 on success.
print_repeated_string () {
    local ch="${1}"
    local len="${2}"
    printf "%${len}s" | tr ' ' "${ch}"
}

##
# Logs a message with tag "get_signed_certificate".
# Arguments:
#   @param Message to be logged.
# Outputs:
#   @return Exit code of logger utility.
log_message () {
    logger -t "${PROGNAME:-get_signed_certificate}[$$]" "${1}"
}