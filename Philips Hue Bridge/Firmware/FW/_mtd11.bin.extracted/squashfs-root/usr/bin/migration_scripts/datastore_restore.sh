#!/bin/ash
# Copyright (c) 2025 Signify Holding

HUE_MIGRATION_ARCHIVE=/home/migration.tar.gz
HUE_MIGRATION_DIR=/home/migration
HUE_IPBRIDGE_PERSISTENT=/home/ipbridge/var

EXITCODE=100 # # just to make sure datastore_backup_restore_init was called

source /usr/bin/migration_scripts/datastore_common.sh

datastore_backup_restore_init "datastore_restore.sh"

run_process test -f ${HUE_MIGRATION_ARCHIVE}
if [ "${EXITCODE}" != "0" ]
then
    log "No backup found"
    exit 1
fi

log "Restoring from backup"
rm -rf ${HUE_MIGRATION_DIR}
run_process tar -xzf ${HUE_MIGRATION_ARCHIVE} -C /
if [ "${EXITCODE}" != "0" ]
then
    log "Failed to extract backup"
    exit 1
fi

# stop all daemons
/etc/init.d/behaviord stop
/etc/init.d/groups stop
/etc/init.d/stream stop
/etc/init.d/ipbridge stop

# restore datastore
determineSwVersion

run_process behaviord --restore
run_process groups --restore
run_process ipbridge --restore -h /home -p ${HUE_IPBRIDGE_PERSISTENT} -v "${SWVERSION}" $(formatArgFromUbootEnvVar -k portal) $(formatArgFromUbootEnvVar -e eui64)
run_process stream --restore --host-out=127.0.0.1 --tokenstore-path=/home/.config/tokenstore

# if restore failed, execute recovery script to clean up the impaired state
if [ "${EXITCODE}" != "0" ]
then
    log "Restore failed, executing recovery script"
    /usr/bin/migration_scripts/datastore_recover.sh
fi

rm -rf ${HUE_MIGRATION_DIR}

# restart broker to clear retained messages
/etc/init.d/mosquitto restart

# start all daemons
/etc/init.d/ipbridge start
/etc/init.d/groups start
/etc/init.d/stream start
/etc/init.d/behaviord start

log "Restore completed, exit code: $EXITCODE"
exit $EXITCODE
