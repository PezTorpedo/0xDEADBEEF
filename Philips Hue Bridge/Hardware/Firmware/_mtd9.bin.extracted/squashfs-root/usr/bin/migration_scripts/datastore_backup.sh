#!/bin/ash
# Copyright (c) 2025 Signify Holding

HUE_IPBRIDGE_PERSISTENT=/home/ipbridge/var
HUE_MIGRATION_DIR=/home/migration
HUE_DATASTORE_ARCHIVE=/home/migration.tar.gz
HUE_DATASTORE_TMP_ARCHIVE="${HUE_DATASTORE_ARCHIVE}.tmp"

EXITCODE=100 # just to make sure datastore_backup_restore_init was called

source /usr/bin/migration_scripts/datastore_common.sh

datastore_backup_restore_init "datastore_backup.sh"

# prepare
rm -rf ${HUE_MIGRATION_DIR}
rm ${HUE_DATASTORE_ARCHIVE}
rm ${HUE_DATASTORE_TMP_ARCHIVE}

log "Stopping all daemons"
/etc/init.d/behaviord stop
/etc/init.d/groups stop
/etc/init.d/stream stop
/etc/init.d/ipbridge stop

log "Backup datastore start"
determineSwVersion

run_process behaviord --backup
run_process groups --backup
run_process ipbridge --backup -h /home -p ${HUE_IPBRIDGE_PERSISTENT} -v "${SWVERSION}" $(formatArgFromUbootEnvVar -k portal) $(formatArgFromUbootEnvVar -e eui64)
run_process stream --backup --host-out=127.0.0.1 --tokenstore-path=/home/.config/tokenstore

log "Backup completed, exit code: $EXITCODE"

# Archive the backup and clean up the /home/migration folder
# =========================================================================================
run_process tar -czf ${HUE_DATASTORE_ARCHIVE} ${HUE_MIGRATION_DIR}
rm -rf ${HUE_MIGRATION_DIR}

log "Backup archive created, exit code: $EXITCODE"

log "Starting back all daemons"
/etc/init.d/ipbridge start
/etc/init.d/groups start
/etc/init.d/stream start
/etc/init.d/behaviord start

exit $EXITCODE
