#!/bin/ash
# Copyright (c) 2025 Signify Holding

HUE_MIGRATION_ARCHIVE=/home/migration.tar.gz
HUE_MIGRATION_DIR=/home/migration
HUE_IPBRIDGE_PERSISTENT=/home/ipbridge/var

EXITCODE=100 # # just to make sure datastore_backup_restore_init was called

source /usr/bin/migration_scripts/datastore_common.sh

datastore_backup_restore_init "datastore_restore_migration_device_list.sh"

run_process test -f ${HUE_MIGRATION_ARCHIVE}
if [ "${EXITCODE}" != "0" ]
then
    log "No backup found"
    exit 1
fi

log "Restoring trustcenter from backup"
rm -rf ${HUE_MIGRATION_DIR}
run_process tar -xzf ${HUE_MIGRATION_ARCHIVE} -C /
if [ "${EXITCODE}" != "0" ]
then
    log "Failed to extract backup"
    exit 1
fi

# stop ipbridge
/etc/init.d/ipbridge stop

# restore trustcenter
determineSwVersion

run_process ipbridge --restore=trustcenter -h /home -p ${HUE_IPBRIDGE_PERSISTENT} -v "${SWVERSION}" $(formatArgFromUbootEnvVar -k portal) $(formatArgFromUbootEnvVar -e eui64)

# Cleanup migration dir
rm -rf ${HUE_MIGRATION_DIR}

# start ipbridge
/etc/init.d/ipbridge start

log "Restore trustcenter completed, exit code: $EXITCODE"
exit $EXITCODE
