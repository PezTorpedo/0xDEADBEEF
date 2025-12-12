determineSwVersion() {
	SWVERSION_FILE=${SWVERSION_FILE:-/etc/swversion}
	# Determine system swversion
	[ -f "${SWVERSION_FILE}" ] && SWVERSION=$(cat "${SWVERSION_FILE}") || SWVERSION=""
}