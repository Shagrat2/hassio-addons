#!/usr/bin/env bashio
set -e
CONFIG_PATH=/data/options.json


bashio::log.info "Starting ..."

#start the addon
python main.py