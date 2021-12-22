ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base-python:3.7-alpine3.14
FROM $BUILD_FROM

# Set shell
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Setup base system
ARG BUILD_ARCH=amd64

#copy the app
COPY rootfs/app /app
COPY rootfs/run.sh /

#requirements
RUN pip install --no-cache-dir requests pyserial paho-mqtt

#make it run
RUN chmod a+x /run.sh

WORKDIR /app/
CMD [ "/run.sh" ]

# Build arguments
ARG BUILD_ARCH
ARG BUILD_DATE
ARG BUILD_REF
ARG BUILD_VERSION

# Labels
LABEL \
  io.hass.name="Energomera iek61107" \
  io.hass.description="Reading readings from the Energomera meter using the iek61107 protocol" \
  io.hass.arch="${BUILD_ARCH}" \
  io.hass.type="addon" \
  io.hass.version=${BUILD_VERSION} \
  maintainer="Shagrat2 <ivan@jad.ru>" \
  org.label-schema.description="Reading readings from the Energomera meter using the iek61107 protocol" \
  org.label-schema.build-date=${BUILD_DATE} \
  org.label-schema.name="Energomera iek61107" \
  org.label-schema.schema-version="1.0" \
  org.label-schema.url="https://github.com/Shagrat2/hassio-addons" \
  org.label-schema.usage="https://github.com/Shagrat2/hassio-addons/blob/master/README.md" \
  org.label-schema.vcs-ref=${BUILD_REF} \
  org.label-schema.vcs-url="https://github.com/Shagrat2/hassio-addons" \
  org.label-schema.vendor="Shagrat2 <ivan@jad.ru>"