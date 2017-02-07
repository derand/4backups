# Default server host
#
# VERSION               0.1
#
# Based on: https://github.com/nick81/docker-mongodb-arm
#   Latest version of mongodb not working on rpi used mongodb-3.0.4-1
#
# BUILD-USING:   docker build --rm -t derand/backup:mysql-armhf .
# RUN-USING:     docker run --log-driver json-file --log-opt max-size=50k --log-opt max-file=1 --detach=true -v /home/pi/docker/backups/share:/mnt -v /home/pi/docker/backups/mysql-armhf/db_credencials:/db_credencials --name mysql_backup derand/backup:mongo-armhf
#

FROM     resin/rpi-raspbian:jessie
MAINTAINER Andrey Derevyagin "2derand@gmail.com"

ENV BACKUP_PATH="/mnt"                 \
    CREDENCIALS_PATH="/db_credencials" \
    OWNER_PERMISSIONS=1

COPY entrypoint.sh /

RUN chmod +x /entrypoint.sh && \
    apt-get update && \
    apt-get -y install --no-install-recommends mysql-client && \
    rm -fr /var/lib/apt/lists/*

ENTRYPOINT ["/entrypoint.sh"]
