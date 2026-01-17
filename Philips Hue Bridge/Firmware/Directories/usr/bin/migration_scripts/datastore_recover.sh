#!/bin/ash
# Copyright (c) 2025 Signify Holding

HUE_RECOVERY_ARCHIVE=/etc/migration/recovery.tar.gz
HUE_MIGRATION_DIR=/home/migration
HUE_IPBRIDGE_PERSISTENT=/home/ipbridge/var

EXITCODE=100 # # just to make sure datastore_backup_restore_init was called

source /usr/bin/migration_scripts/datastore_common.sh

datastore_backup_restore_init "datastore_recover.sh"

run_process test -f ${HUE_RECOVERY_ARCHIVE}
if [ "${EXITCODE}" != "0" ]
then
    log "No recovery archive found"
    exit 1
fi

log "Restoring from recovery archive"
rm -rf ${HUE_MIGRATION_DIR}
run_process tar -xzf ${HUE_RECOVERY_ARCHIVE} -C /
if [ "${EXITCODE}" != "0" ]
then
    log "Failed to extract recovery archive"
    exit 1
fi

determineSwVersion

run_process behaviord --restore
run_process groups --restore
run_process ipbridge --restore -h /home -p ${HUE_IPBRIDGE_PERSISTENT} -v "${SWVERSION}" $(formatArgFromUbootEnvVar -k portal) $(formatArgFromUbootEnvVar -e eui64)
run_process stream --restore --host-out=127.0.0.1 --tokenstore-path=/home/.config/tokenstore

log "Recovery completed, exit code: $EXITCODE"
exit $EXITCODE