ARG BUILD_FROM
FROM $BUILD_FROM

# Install requirements for add-on
RUN \
  apk add --no-cache \
  python3

#python3 -m pip install pyserial
RUN pip install pyserial

COPY . /srv
RUN chmod a+x /srv/energomera.sh

WORKDIR /share

CMD [ "/srv/run_addon.sh" ]