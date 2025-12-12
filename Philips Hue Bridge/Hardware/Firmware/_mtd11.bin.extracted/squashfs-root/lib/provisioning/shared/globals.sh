#!/usr/bin/env ash
# Copyright (c) 2020 Signify Holding
# shellcheck shell=dash
# shellcheck disable=SC2034,SC2154

init_globals () {
    bridge_id=$(fw_printenv -n eui64)
    readonly bridge_id
    portal_key=$(fw_printenv -n portal)
    readonly portal_key
    device_name=$(fw_printenv -n board)
    readonly device_name

    readonly openssl_cfg="${ROOT}/etc/ca/openssl.cfg"
    readonly private_key_file="${certificate_directory}/private_key.pem"

    readonly certificate_file="${certificate_directory}/certificate.crt"
    readonly service_file="${certificate_directory}/service.json"
    readonly checksums_file="${certificate_directory}/checksums.sha1"

    readonly https_ca_cert_file="${ROOT}/etc/ca-certificates/ca.ecc.cert-and-crls.pem"    

    readonly country="NL"
    readonly organization="Philips Hue"

    readonly renew_window=10 # in percentage

    readonly hbdev_hkdf_ctx="iot-v1-dev"
    readonly test_hkdf_ctx="iot-v1-system"
    readonly prod_hkdf_ctx="iot-v1-prod"
    readonly local_hkdf_ctx="signingKey_PoC"

    readonly hbdev_server_url="https://provision-dev.meethue.com"
    readonly test_server_url="https://provision-system.meethue.com"
    readonly prod_server_url="https://provision.meethue.com"
    readonly local_server_url="http://localhost:3000"

    readonly protocol_version="3"
    readonly key_version="2"
    readonly cert_type="iot-v1"

    # shellcheck disable=SC2002
    sw_version=$(cat "${ROOT}/etc/swversion" | tr -d '\n')
    readonly sw_version

    readonly max_req_time="${MAX_REQ_TIME:-15}"
    readonly backoff_base="${BACKOFF_BASE:-60000}"
    readonly backoff_max="${BACKOFF_MAX:-10800000}"
    readonly topic_prov_status="status/provisioning/provisioning_state"
    readonly status_msg_success="1"
    readonly status_msg_failed="0"
}
