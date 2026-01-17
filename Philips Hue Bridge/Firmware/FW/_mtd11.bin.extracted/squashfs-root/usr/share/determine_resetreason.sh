setResetReason() {
	local REASON=$1;shift
	echo "${REASON}" > ${HUE_IPBRIDGE_RESETREASON}
}

determineResetReason() {
	local VALUE=$(fw_printenv -n resetreason 2>/dev/null)
	if [ -n "${VALUE}" ]; then
		setResetReason ${VALUE}
		fw_setenv resetreason
	else
		setResetReason ${WATCHDOG_DETAILEDREASON_POWER_ON}
	fi
}