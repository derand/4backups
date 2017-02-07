#!/bin/bash
#
# Writed by Andrey Derevyagin on 29/01/2017

set -e

date
cd $BACKUP_PATH
python /app/gdrive_backup.py

# change premissions
if [ "$OWNER_PERMISSIONS" -ne 0 ] ; then
    chown -R `stat -c "%u:%g" $BACKUP_PATH` $BACKUP_PATH
fi
