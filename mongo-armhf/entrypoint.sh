#!/bin/bash
#
# Writed by Andrey Derevyagin on 03/03/2015

set -e

#MONGO_FOLDER='/mongodb_rpi/'
MONGO_FOLDER=''
MDUMP_PATH="${MONGO_FOLDER}mongodump"
MONGO_PATH="${MONGO_FOLDER}mongo"
#OUT_PATH="."
#OUT_PATH="/mnt"
#OUT_CREDENCIALS_PATH="/mnt/.db_credencials"
#CREDENCIALS_PATH="/db_credencials"

#credencials file example:
#<server:port> <user> <password> databasename
#ds037551.mongolab.com:37551 XhkM9g un36jWydqXZQ tests
# copy credencials to container
#if [ -f $OUT_CREDENCIALS_PATH ]; then
#    cp $OUT_CREDENCIALS_PATH $CREDENCIALS_PATH
#fi


#IFS=$'\n' GLOBIGNORE='#' :; DBS=($(cat $CREDENCIALS_PATH))
#IFS=$'\n' read -d '' -r -a DBS < $CREDENCIALS_PATH
#IFS=$'\n' read -d '' -r -a DBS < $CREDENCIALS_PATH

while IFS='' read -r line || [[ -n "$line" ]]; do
    IFS=' ' read -a info <<< $line

    echo "Working with: ${info[3]} server: ${info[0]}"
    $MDUMP_PATH -h ${info[0]} -d ${info[3]} -u ${info[1]} -p ${info[2]} -o $BACKUP_PATH &> /dev/null
    if [ $? -ne 0 ]; then
        echo "Full db error. Try dump each collection"
        IFS=$'\n'
        collections=( $(echo 'show collections' | $MONGO_PATH ${info[0]}/${info[3]} -u ${info[1]} -p ${info[2]} | sed '$d' | sed '/connecting to/,// !d' | sed '1d') )
        for c in "${collections[@]}"; do
            echo "Collection: $c"
            $MDUMP_PATH -h ${info[0]} -d ${info[3]} -c $c -u ${info[1]} -p ${info[2]} -o $BACKUP_PATH &> /dev/null
        done
    fi
    #echo ${info[1]} ${info[3]}
done < $CREDENCIALS_PATH

# change premissions
if [ "$OWNER_PERMISSIONS" -ne 0 ] ; then
    chown -R `stat -c "%u:%g" $BACKUP_PATH` $BACKUP_PATH
fi

