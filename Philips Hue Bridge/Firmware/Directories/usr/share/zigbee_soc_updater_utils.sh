
ZIGBEE_UPDATER=/usr/sbin/zigbee_soc_updater
ZIGBEE_UPDATE_FILE=/lib/firmware/zigbee.sbl
ZIGBEE_VERSION_FILE=/lib/firmware/zigbee.version

zigbeeUpdater() {
    ${ZIGBEE_UPDATER} -z ${HUE_IPBRIDGE_TTY} $*
}

isZigbeeSocUpToDate() {
    zigbeeUpdater -c ${ZIGBEE_VERSION_FILE}
}

updateZigbeeSoc() {
    zigbeeUpdater -u ${ZIGBEE_UPDATE_FILE}
}

factoryresetZigBeeSocIfNecessary() {
	local reset_button_state=$(grep "Reset button" /sys/kernel/debug/gpio | awk '{print ($7=="hi")}')
	if [ "${reset_button_state}" == "1" ]; then
		log "Reset button held at boot, will factoryreset Zigbee SoC"
		zigbeeUpdater -r
	fi
}

updateZigBeeSocIfNecessary() {
	local EXPECTED_SOC_VERSION=$(cat ${ZIGBEE_VERSION_FILE})
	local CPU_ARCH=$(uname -m)

	if [[ ${CPU_ARCH} != mips ]]; then
		log "Skip Zigbee Soc update for cpu architecture: ${CPU_ARCH}"
	elif isZigbeeSocUpToDate; then
		log "Zigbee SoC up to date: ${EXPECTED_SOC_VERSION}"
	else
		log "Updating Zigbee SoC to ${EXPECTED_SOC_VERSION}"
		if ! updateZigbeeSoc; then
			error "Cannot update Zigbee SoC"
		fi
	fi
}
