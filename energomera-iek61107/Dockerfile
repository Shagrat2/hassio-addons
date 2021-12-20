#ARG BUILD_FROM
#FROM $BUILD_FROM
FROM python:3

ENV LANG C.UTF-8

RUN python3 -m pip install pyserial

COPY . /srv
RUN chmod a+x /srv/energomera.sh

WORKDIR /share

CMD [ "/srv/run_addon.sh" ]