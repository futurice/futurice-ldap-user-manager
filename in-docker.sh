#!/bin/sh

set -ex

/etc/init.d/postgresql start
su -c 'createdb fum' postgres
su -c 'createuser -s root' postgres

# Venv
if [ !  -d venv ]; then
	rm -rf venv
n
. ./venv/bin/activate

pip install -r requirements.txt

# Npm
npm install

export PATH=$(pwd)/node_modules/.bin/:$PATH
ln -s $(which nodejs) /usr/local/bin/node
assetgen --force --profile dev assetgen.yaml

# Tests LDAP
ldapsearch -H ldap://ldap:389 -D "cn=Directory Manager" -w Admin123 -b "dc=futurice,dc=com"

echo "RUN:  REMOTE_USER=x ./manage.py runserver --nostatic 0.0.0.0:8000"
