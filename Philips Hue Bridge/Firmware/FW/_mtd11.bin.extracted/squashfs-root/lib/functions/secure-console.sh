#!/bin/sh
# Copyright (c) 2019 Signify Holding

unset UBOOT_SECURITY_STRING
unset SHADOW_SECURITY_STRING

abort() {
	echo -e "$*"
	sleep 1
	exit 1
}

isUBootEnvironmentReady() {
	fw_printenv >/dev/null 2>/dev/null
	return $?
}

updateUBootSecurityString() {
	UBOOT_SECURITY_STRING=`fw_printenv -n security 2>/dev/null`
	return $?
}

updateShadowSecurityString() {
	SHADOW_SECURITY_STRING=`awk -F ':' '/^root:/{print $2}' /etc/shadow`
	return $?
}

escapeStringForSed() {
	echo "$1" | sed -e 's/[\/&]/\\&/g'
}

patchShadowSecurityString() {
	local ESCAPED_SECURITY_STRING=`escapeStringForSed $1`
	sed 's/^\(root:\)\([^:]*\)\(.*\)$/\1'${ESCAPED_SECURITY_STRING}'\3/g' /etc/shadow > /etc/shadow.tmp
	local PATCH_RESULT=$?
	sync
	mv /etc/shadow.tmp /etc/shadow
	sync
	return ${PATCH_RESULT}
}

syncShadowWithUBootSecurityString() {
	updateUBootSecurityString
	updateShadowSecurityString
	[[ -z ${SHADOW_SECURITY_STRING} ]] && patchShadowSecurityString ${UBOOT_SECURITY_STRING} || return 1
	return $?
}

if ! isUBootEnvironmentReady; then
	abort "Init in progress: Please try again later..."
fi

if ! syncShadowWithUBootSecurityString; then
	unset UBOOT_SECURITY_STRING
fi

