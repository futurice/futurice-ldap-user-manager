#! /usr/bin/env bash

set -u  # exit if using uninitialised variable
set -e  # exit if some command in this script fails
trap "echo $0 failed because a command in the script failed" ERR

sudo -u postgres createuser vagrant
sudo -u postgres psql -c 'alter user vagrant with createdb' postgres

# fragile: disable password
sed -e 's|^host    all             all             127.0.0.1/32            md5$|host    all             all             127.0.0.1/32            trust|' -i /etc/postgresql/9.*/main/pg_hba.conf

service postgresql restart
