#!/bin/bash
#
# Writed by Andrey Derevyagin on 29/01/2017

set -e

cd /tmp

while IFS='' read -r line || [[ -n "$line" ]]; do
    IFS=' ' read -a info <<< $line
    HOST=${info[0]}
    POST=${info[1]}
    USER=${info[2]}
    PASS=${info[3]}
    DB=${info[4]}

    echo -n "Working with: $DB server: $HOST  " && date
    mysqldump --host="$HOST" --port "$PORT" -u "$USER" -p$PASS "$DB" > $DB.sql
    if [ $? -ne 0 ]; then
        echo "Error .... try to repeat" 
        mysqldump --host="$HOST" --port "$PORT" -u "$USER" -p$PASS "$DB" > $DB.sql
        if [ $? -ne 0 ]; then
            echo "Baaaaaaad!!!" 
            continue
        fi
    fi
    tar -zcvf "$BACKUP_PATH/$DB.sql.tgz" $DB.sql
    rm $DB.sql
done < $CREDENCIALS_PATH

# change premissions
if [ "$OWNER_PERMISSIONS" -ne 0 ] ; then
    chown -R `stat -c "%u:%g" $BACKUP_PATH` $BACKUP_PATH
fi
