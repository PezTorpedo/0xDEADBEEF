#!/bin/sh
# Copyright (c) 2019 Signify Holding

. /lib/functions/secure-console.sh

DEV_KEY_FILE=/rom/home/swupdate/certs/RSA_dev_01_pub.pem
SECRET_PHRASE_FILE=/tmp/secret_phrase
PEM_FILE=/etc/secret-key.pub

print_encryption_method() {
  method=`awk -F '$' '/^root:/{print $2}' /etc/shadow`
  [ -n "$method" ] && echo "$method"
}

print_salt() {
  salt=`awk -F '$' '/^root:/{print $3}' /etc/shadow`
  [ -n "$salt" ] && echo "$salt"
}

verify_secret(){
# check if secret file exist, exit immediately if already in /tmp
[ -f "${SECRET_PHRASE_FILE}" ] && exit

# check PEM file, exit if file not found
[ ! -f "${PEM_FILE}" ] && exit

print_encryption_method
print_salt

# read secret from console
read -s secret
[ -n "$secret" ] && echo "$secret" | openssl base64 -d > "${SECRET_PHRASE_FILE}" || exit

BOOT_SECURITY_STRING=`fw_printenv -n security 2>/dev/null`
EUI64=`fw_printenv -n eui64 | awk '{print toupper($0)}')`

# check secret
result=$(echo "$EUI64 $BOOT_SECURITY_STRING" | openssl dgst -sha256 -verify ${PEM_FILE} -signature ${SECRET_PHRASE_FILE})
if [ "Verified OK" = "$result" ]; then
  # check password
  exec /bin/login
  rm -f ${SECRET_PHRASE_FILE}
fi
}

if [ ! -f "${DEV_KEY_FILE}" ]; then
  verify_secret
else
  exec /bin/ash --login
fi
