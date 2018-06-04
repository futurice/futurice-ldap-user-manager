#! /usr/bin/env bash

set -u  # exit if using uninitialised variable
set -e  # exit if some command in this script fails
trap "echo $0 failed because a command in the script failed" ERR

apt-get update
apt-get install -y \
	build-essential htop \
	python-dev python-setuptools python-pip python-virtualenv python-pkg-resources \
	libxml2-dev libxslt1-dev libffi-dev \
	libcurl4-openssl-dev libssl-dev zlib1g-dev libpcre3-dev \
	libldap2-dev libsasl2-dev \
	libjpeg-dev \
	libfreetype6-dev \
	postgresql libpq-dev libsqlite3-dev \
	npm \
	memcached curl

ln -s /usr/bin/nodejs /usr/bin/node

cd /tmp
curl https://www.python.org/ftp/python/2.7.15/Python-2.7.15.tgz -o python2.tgz
tar -xzvf python2.tgz
cd Python-2.7.15/
./configure --with-ensurepip=install --enable-loadable-sqlite-extensions
make -j2 install
ln -sf /usr/local/bin/python2.7 /usr/bin/python
