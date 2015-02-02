#! /usr/bin/env bash

set -u  # exit if using uninitialised variable
set -e  # exit if some command in this script fails
trap "echo $0 failed because a command in the script failed" ERR


createdb fum

# To run ‘datamigrate’ at provision-*.sh time, we need these commands
# which also run at always-*.sh time.
cd /vagrant
mkdir -p media/portraits/full media/portraits/thumb
python manage.py test --settings=fum.settings.test
./manage.py migrate --noinput

./manage.py datamigrate
