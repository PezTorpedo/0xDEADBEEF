#!/usr/bin/env ash
# Copyright (c) 2020 Signify Holding
# shellcheck shell=dash

##
# Configures shell to exit on a non-success command exit code.
# Outputs:
#   @return 0 on success.
set_exit_on_errors () {
    set -e
}

##
# Configures shell to ignore a non-success command exit code.
# Outputs:
#   @return 0 on success.
clear_exit_on_errors () {
    set +e
}

##
# Sets an exit callback trap.
# Arguments:
#   @param Callback function/script name.
# Outputs:
#   @return 0 on success.
set_exit_trap () {
    local callback=${1}
    # shellcheck disable=SC2064
    trap "${callback}" EXIT
}

##
# Empty function.
# Outputs:
#   @return Always 0.
ignore_errors () {
       :
}

##
# Sets the exit_status global and exits the script.
# Globals:
#   exit_status
# Arguments:
#   @param Exit status to be set.
# Outputs:
#   @return Always 0. 
exit_with () {
    exit_status=${1}
    exit "${exit_status}"
}