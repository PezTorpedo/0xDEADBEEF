
OVERLAY_UPPER_DIR=/overlay/upper
OVERLAY_ROM_DIR=/rom

log() {
	echo "$*" >/dev/console
}

error() {
	log "error: $*"
}

abort() {
	error "$*"
	exit 1
}

is_factory_state() {
	local ROOT_FILE_PATH=${1}
	local UPPER_FILE_PATH=${OVERLAY_UPPER_DIR}/${ROOT_FILE_PATH}
	if [ -f "${UPPER_FILE_PATH}" ]; then
		return 1
	else
		return 0
	fi
}

exit_if_factory_state() {
	local ROOT_FILE_PATH=${1}
	if is_factory_state ${ROOT_FILE_PATH}; then
		log "${ROOT_FILE_PATH} not modified: no need to migrate"
		exit 0
	fi
}

restore_from_rom() {
	local ROOT_FILE_PATH=${1}
	local ROM_FILE_PATH=${OVERLAY_ROM_DIR}/${ROOT_FILE_PATH}
	if cp -a ${ROM_FILE_PATH} ${ROOT_FILE_PATH}; then
		log "restored ${ROOT_FILE_PATH} from ${ROM_FILE_PATH}"
	else
		abort "cannot restore ${ROOT_FILE_PATH} from ${ROM_FILE_PATH}"
	fi
}
