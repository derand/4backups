# Default server host
#
# VERSION               0.1
#
# BUILD-USING:   docker build --rm -t derand/backup:gdrive-armhf .
# RUN-USING:     docker run --log-driver json-file --log-opt max-size=50k --log-opt max-file=1 --detach=true -v /home/pi/docker/backups/share:/mnt --name gdrive_backup derand/backup:gdrive-armhf
#

FROM     derand/base:rpi
MAINTAINER Andrey Derevyagin "2derand@gmail.com"

ENV  BACKUP_PATH="/mnt"   \
     OWNER_PERMISSIONS=1  \
     BACKUP_SHARED=0

COPY app /app
COPY entrypoint.sh /

RUN apt-get update && apt-get install -y --no-install-recommends build-essential software-properties-common \
        python2.7 python-setuptools && \
    easy_install pip && \
    pip install -r /app/requirements.txt && \
    chmod a+x /entrypoint.sh && \
    apt-get purge -y build-essential software-properties-common && apt-get clean -y && apt-get autoclean -y && apt-get autoremove -y && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

ENTRYPOINT ["/entrypoint.sh"]
