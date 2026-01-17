#!/bin/sh
SELF=`basename $0`

set -o pipefail

# Includes
. /lib/functions/mtd.sh

log_tty() {
	log "$*" >/dev/ttyS0
}

log_tty "!!! Executing factoryreset !!!"

upgradeFlags () {
	# set factory reset in progress
	# remove datafs_format contents, so migration runs again in case of downgrade to jffs2
	fw_setenv --script - <<-EOF
	resetting_to_factory 1
	datafs_format
EOF
}

# Copy resetreason if provided
if [ -f /var/platform/ipbridge-resetreason ]; then
	resetreason=`cat /var/platform/ipbridge-resetreason`
	fw_setenv resetreason ${resetreason}
fi

upgradeFlags
shuthuedown
reboot
