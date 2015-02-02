#! /usr/bin/env bash

set -u  # exit if using uninitialised variable
set -e  # exit if some command in this script fails
trap "echo $0 failed because a command in the script failed" ERR

ROOT_DIR=/vagrant
VAGRANT_DIR="$ROOT_DIR"/vagrant

"$VAGRANT_DIR"/apt-get.sh
"$VAGRANT_DIR"/postgresql.sh

# To run ‘datamigrate’ at provision-*.sh time, we need these commands
# which also run at always-*.sh time.
pip install -r "$ROOT_DIR"/requirements.txt
