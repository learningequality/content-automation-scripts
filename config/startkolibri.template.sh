#!/bin/bash
# Startup script for running kolibri all-in-one `pex` file

set -eo pipefail

export KOLIBRI_LANG={{KOLIBRI_LANG}}
export KOLIBRI_HOME={{KOLIBRI_HOME}}
export KOLIBRI_PORT={{KOLIBRI_PORT}}
export KOLIBRI_PEX_FILE={{KOLIBRI_PEX_FILE}}
export KOLIBRI_RUN_MODE="demoserver"
# Uncomment next line to import content from develop studio
# export KOLIBRI_CENTRAL_CONTENT_BASE_URL="https://develop.studio.learningequality.org"


# This command was needed for older version of Kolibri to set the default language
# python $KOLIBRI_PEX_FILE language setdefault $KOLIBRI_LANG

exec python $KOLIBRI_PEX_FILE start --foreground --port=$KOLIBRI_PORT
