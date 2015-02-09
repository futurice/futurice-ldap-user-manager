#! /usr/bin/env bash

set -u  # exit if using uninitialised variable
set -e  # exit if some command in this script fails
trap "echo $0 failed because a command in the script failed" ERR

apt-get update
apt-get install -y \
	build-essential htop \
	python-dev python-pip python-virtualenv \
	libxml2-dev libxslt1-dev \
	libcurl4-openssl-dev libssl-dev zlib1g-dev libpcre3-dev \
	libldap2-dev libsasl2-dev \
	libjpeg-dev \
	libfreetype6-dev \
	postgresql libpq-dev \
	npm \
	memcached

ln -s /usr/bin/nodejs /usr/bin/node
