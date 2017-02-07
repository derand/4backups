# Default server host
#
# VERSION               0.3
#
# Based on: https://github.com/nick81/docker-mongodb-arm
#   Latest version of mongodb not working on rpi used mongodb-3.0.4-1
#
# BUILD-USING:   docker build --rm -t derand/backup:mongo-armhf .
# RUN-USING:     docker run --log-driver json-file --log-opt max-size=50k --log-opt max-file=1 --detach=true -v /home/pi/docker/backups/share:/mnt -v /home/pi/docker/backups/mongo-armhf/db_credencials:/db_credencials --name mongo_backup derand/backup:mongo-armhf
#
#                docker commit -a "Andrey Derevyagin <2derand@gmail.com>" -m "Backup from mongolab" 5788292463c0 derand/mongolab_backup:0.2
#

#FROM     yyolk/rpi-archlinuxarm
FROM     cellofellow/rpi-arch
MAINTAINER Andrey Derevyagin "2derand@gmail.com"

ENV BACKUP_PATH="/mnt"                 \
    CREDENCIALS_PATH="/db_credencials" \
    OWNER_PERMISSIONS=1

COPY entrypoint.sh *.tar.xz /

RUN chmod +x /entrypoint.sh && \
    pacman -Syu --noconfirm && \
    pacman-db-upgrade && \
    pacman -U /*.tar.xz --noconfirm && \
    pacman -S mongodb-tools --noconfirm && \
    rm -f /*.tar.xz && \

# Clean up pacman
    bash -c "echo 'y' | pacman -Scc >/dev/null 2>&1" && \
    paccache -rk0 >/dev/null 2>&1 &&  \
    pacman-optimize && \
    rm -r /var/lib/pacman/sync/*

ENTRYPOINT ["/entrypoint.sh"]
