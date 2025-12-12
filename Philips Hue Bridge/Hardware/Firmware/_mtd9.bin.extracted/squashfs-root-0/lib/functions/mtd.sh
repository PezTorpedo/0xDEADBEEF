#!/bin/sh

if [ -z "${SELF}" ]; then
	echo "error: SELF undefined including mtd.sh" >/dev/ttyS0
	exit 1
fi

log() {
	echo "$*"
	logger -p daemon.notice -t ${SELF} "$*"
}

error() {
	echo "error: $*" >&2
	logger -p daemon.error -t ${SELF} "$*"
}

abort() {
	error "$*"
	exit 1
}

pipeToLog() {
	local PREFIX="$1"
	local LINE
	while read LINE; do
		log "${PREFIX:+${PREFIX}: }${LINE}"
	done
}

nameToMtdDevice() {
	local PARTITION_NAME=$1
	awk '
		BEGIN {
			FS=":"
		}
		/^mtd[0-9]+:[ \t]+([0-9a-f]{8}[ \t]){2}"'${PARTITION_NAME}'"/ {
			print $1
		}
	' /proc/mtd
}

isNandDevice() {
	local DEV_TYPE=`cat /sys/class/mtd/$1/type`
	if [ "${DEV_TYPE}" != "nor" ]; then
		return 0
	else
		return 1
	fi
}

eraseNand() {
	local DEVICE=$1
	log "${DEVICE}: erasing (NAND)..."
	if ! flash_eraseall -q /dev/${DEVICE} 2>&1; then
		return 1
	else
		return 0
	fi | pipeToLog ${DEVICE}
}

eraseNor() {
	local DEVICE=$1
	log "${DEVICE}: erasing (NOR)..."
	if ! mtd erase ${DEVICE} 2>&1; then
		return 1
	else
		return 0
	fi | pipeToLog ${DEVICE}
}

eraseMtd() {
	local DEVICE=$1
	if isNandDevice ${DEVICE}; then
		eraseNand ${DEVICE}
		return $?
	else
		eraseNor ${DEVICE}
		return $?
	fi
}

writeNand() {
	local DEVICE=$1
	log "${DEVICE}: writing (NAND) ..."
	if ! nandwrite -p /dev/${DEVICE} - 2>&1; then
		return 1
	else
		return 0
	fi | pipeToLog ${DEVICE}
}

writeNor() {
	local DEVICE=$1
	log "${DEVICE}: writing (NOR) ..."
	if ! mtd write - ${DEVICE} 2>&1; then
		return 1
	else
		return 0
	fi | pipeToLog ${DEVICE}
}

writeMtd() {
	local DEVICE=$1
	if isNandDevice ${DEVICE}; then
		writeNand ${DEVICE}
		return $?
	else
		writeNor ${DEVICE}
		return $?
	fi
}

getSysfsValue() {
	cat /sys/class/mtd/$1/$2
}

getPageSize() {
	getSysfsValue $1 subpagesize
}

getCorrectedBits() {
	getSysfsValue $1 corrected_bits
}

getEccFailures() {
	getSysfsValue $1 ecc_failures
}

readNandBytes() {
	local DEVICE=${1};shift
	local SIZE=${1};shift
	local PAGE_SIZE=`getPageSize ${DEVICE}`
	local FULL_PAGE_COUNT
	local REMAINING_BYTES
	let "FULL_PAGE_COUNT=${SIZE}/${PAGE_SIZE}"
	let "REMAINING_BYTES=${SIZE}%${PAGE_SIZE}"
	# nanddump -l ${SIZE} increases the size to a page boundary. It therefore is necessary to crop the result. But there
	# is a catch: Whoever reads from the stdout of nanddump, has to read chunks that do not exceed page boundaries. We therefore
	# use two dd reads: The first reads all the full pages, the second reads the remaining bytes. The result is that stdout
	# outputs exactly ${SIZE} bytes.
	nanddump -l ${SIZE} /dev/${DEVICE} | ( \
		dd bs=${PAGE_SIZE} count=${FULL_PAGE_COUNT} && \
		if [ "${REMAINING_BYTES}" -ne "0" ]; then \
			dd bs=${REMAINING_BYTES} count=1; \
		fi \
	)
}

readMtdBytes() {
	local DEVICE=$1;shift
	local SIZE=$1
	if isNandDevice ${DEVICE}; then
		readNandBytes ${DEVICE} ${SIZE}
		return $?
	else
		error "readNorBytes not yet implemented"
		return 1
	fi
}
