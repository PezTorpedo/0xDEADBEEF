#!/usr/bin/env ash
# Copyright (c) 2020 Signify Holding
# shellcheck shell=dash

##
# Runs a given command with a timeout.
# The command is run in a separate process.
# The process is killed if the time expires.
# Arguments:
#   @param Timeout period.
#   @param The command to be executed.
# Outputs:
#   @return Exit code of the command. 255 if timer expired.
timeout () {
    local period
    local cmd
    local cmd_pid
    local wdt_pid
    local retval
    
    period="${1}"
    shift
    cmd="${*}"

    ${cmd} &
    cmd_pid=$!
    (
        sleep "${period}"
        kill ${cmd_pid} 2> /dev/null
    ) &
    wdt_pid=$!
    wait ${cmd_pid}
    retval=$?

    kill ${wdt_pid} 2> /dev/null

    if [ "${retval}" -eq 143 ]; then # 128 + SIGTERM means it was killed by timeout
        return 255
    fi

    return ${retval}
}

##
# Runs a command until successful completion.
# Between each run, this command sleeps for a given duration.
# Arguments:
#   @param Waitin period
#   @param Command to be run.
# Outputs:
#   No output by this command.
#   @return 0 always.
repeat_until_success () {
    local wait_period
    local cmd

    wait_period="${1}"
    shift
    cmd="${*}"

    until ${cmd}; do
        sleep "${wait_period}"
    done
}
