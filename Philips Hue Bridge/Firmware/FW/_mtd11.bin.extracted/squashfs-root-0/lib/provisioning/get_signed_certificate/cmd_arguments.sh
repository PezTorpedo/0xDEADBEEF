#!/usr/bin/env ash
# Copyright (c) 2020 Signify Holding
# shellcheck shell=dash
# shellcheck disable=SC2034

##
# Shows the usage of get_signed_certificate command.
# Outputs:
#   Usage is printed to stdout.
_show_usage() {
    echo "incorrect arguments provided"
    echo ""
    echo "use as: ${0} [reason] [destination_path]"
}

##
# Processes the command line arguments.
# Globals:
#   certificate_reason
#   certificate_directory
# Arguments:
#   @param Certificate reason.
#   @param Certificate directory.
#   @param Reason which triggered provisioning
# Outputs:
#   Prints the usage on error.
#   @return 0 on success, 1 on failure.
process_cmd_arguments () {
    # needs to be called with "$@"
    if [ $# != 3 ]; then
        _show_usage
        return 1
    fi
    certificate_reason="$1"
    certificate_directory="$2"
    provisioning_reason="$3"

    return 0
}