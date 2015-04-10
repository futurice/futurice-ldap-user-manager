#! /usr/bin/env bash

set -u  # exit if using uninitialised variable
set -e  # exit if some command in this script fails
trap "echo $0 failed because a command in the script failed" ERR


cd /vagrant

npm install

mkdir -p media/portraits/full media/portraits/thumb media/portraits/badge
python manage.py test --settings=fum.settings.test --noinput fum

./manage.py migrate --noinput
./manage.py collectstatic --noinput


# TODO: improve this
# Run 2 processes in the background
PATH=./node_modules/.bin:$PATH ./watcher.py &
REMOTE_USER=`cat vagrant/REMOTE_USER` \
	./manage.py runserver --nostatic 0.0.0.0:8000 &
