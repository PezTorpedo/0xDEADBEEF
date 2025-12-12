#!/usr/bin/env ash
# Copyright (c) 2020 Signify Holding
# shellcheck shell=dash
# shellcheck disable=SC2034
# shellcheck disable=SC2154

##
# Replaces new lines with \n sequence.
# Arguments:
#   stdin is used as the input stream.
# Outputs:
#   Processed lines are printed to stdout.
#   @return 0 on success.
_replace_newlines_with_sequence () {
    sed ':a;N;$!ba;s/\n/\\n/g'
}

##
# Loads the signing keys for B2PE and PE2B.
# Globals;
#   portal_key
#   bridge_id
#   hkdf_ctx
#   signingKey_B2PE
#   signingLey_PE2B
# Outputs:
#   @return 0 on success.
load_signing_keys () {
    local signingKey
    signingKey=$(hkdf 64 "${portal_key}" "${bridge_id}" "${hkdf_ctx}")
    signingKey_B2PE=$(valueof "${signingKey}" | cut -c1-64)
    readonly signingKey_B2PE
    signingKey_PE2B=$(valueof "${signingKey}" | cut -c65-128)
    readonly signingKey_PE2B
}

##
# Creates a private key file.
# Globals:
#   private_key_file
# Outputs:
#   @return 0 on success.
create_private_key () {
    openssl ecparam -name prime256v1 -genkey -out "${private_key_file}"
}

##
# Creates CSR.
# Globals:
#   country
#   organization
#   bridge_id
#   openssl_cfg
#   private_key_file
# Outputs:
#   Prints the generated CSR to stdout.
#   @return 0 on success.
create_csr () {
    local subj="/C=${country}/O=${organization}/CN=${bridge_id}"
    openssl req -new -config "${openssl_cfg}" -extensions client_cert -key "${private_key_file}" -batch -subj "${subj}" | _replace_newlines_with_sequence
}
