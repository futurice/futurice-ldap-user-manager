#! /usr/bin/env bash

set -u  # exit if using uninitialised variable
set -e  # exit if some command in this script fails
trap "echo $0 failed because a command in the script failed" ERR


cd /vagrant

echo "NPM version: $(npm -version)"
npm install

mkdir -p media/portraits/full media/portraits/thumb media/portraits/badge

# The test fum.api.tests.ApiTestCase.test_user fails if run via the vagrant
# shell provisioner or via ‘vagrant ssh -c 'python manage.py test …'’.
# self.ldap_val('mail', user) returns [] instead of raising KeyError.
# The test succeeds if run via:
# ― ‘vagrant ssh’ followed by ‘python manage.py test …’
# ― ‘python manage.py test …’ on a dev machine
# ― .travis.yml
# Adding a few environment variable (with any name and value) seems to solve
# the problem.
#
# TODO: understand the cause of this.
# Va=a Vb=b Vc=c python manage.py test --settings=fum.settings.test --noinput fum

./manage.py migrate --noinput
./manage.py collectstatic --noinput


# TODO: improve this
# Run 2 processes in the background
PATH=./node_modules/.bin:$PATH ./watcher.py &
REMOTE_USER=`cat vagrant/REMOTE_USER` \
	./manage.py runserver --nostatic 0.0.0.0:8000 &
