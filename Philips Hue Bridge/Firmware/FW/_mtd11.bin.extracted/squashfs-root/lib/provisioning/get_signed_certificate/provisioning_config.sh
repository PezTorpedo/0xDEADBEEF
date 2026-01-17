#!/usr/bin/env ash
# Copyright (c) 2021 Signify Holding
# shellcheck shell=dash
# shellcheck disable=SC2034
# shellcheck disable=SC2154

##
# Initializes the CTN based globals: server_url and hkdf_ctx.
# Globals:
#   prod_server_url
#   prod_hkdf_ctx
#   test_server_url
#   test_hkdf_ctx
#   hbdev_server_url
#   hbdev_hkdf_ctx
#   local_server_url
#   local_hkdf_ctx
#   error_no_ctn
#   server_url
#   hkdf_ctx
# Outputs:
#   @return Return code for fw_printenv
set_ctn_dependent_variables () {
    local url
    local ctn
    local ctx
    local env_check_return_code

    ctn=$(fw_printenv -n ctn)
    # Provisioning tests define the uboot variable to bypass the hardcoded 
    # server URLs
    fake_server_url=$(fw_printenv -n test_provisioning_server_url || true)
    env_check_return_code=$?
    case ${ctn} in
        "HueBridge2K15")
            url="${prod_server_url}"
            ctx="${prod_hkdf_ctx}"
            ;;
        "HBsystem"|"HBPortal")
            if [ -n "$fake_server_url" ]
            then
                url="${fake_server_url}"
            else
                url="${test_server_url}"
            fi

            ctx="${test_hkdf_ctx}"
            ;;
        "HBDev")
            url="${hbdev_server_url}"
            ctx="${hbdev_hkdf_ctx}"
            ;;
        "localhost")
            url="${local_server_url}"
            ctx="${local_hkdf_ctx}"
            ;;
        *)
            log_message "No CTN, exiting..."
            exit_with "${error_no_ctn}"
            ;;
    esac

    readonly server_url="${url}"
    readonly hkdf_ctx="${ctx}"
    return ${env_check_return_code}
}