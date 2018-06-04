#! /usr/bin/env bash

set -u  # exit if using uninitialised variable
set -e  # exit if some command in this script fails
trap "echo $0 failed because a command in the script failed" ERR

ROOT_DIR="/vagrant"

pip install -r "$ROOT_DIR"/requirements.txt

echo "NPM:$(npm --version||true) NODE:$(node --version||true)"
NODE_VERSION=10.3.0
mkdir -p /tmp/node
wget -qO /tmp/node.tar.gz https://nodejs.org/dist/v$NODE_VERSION/node-v$NODE_VERSION-linux-x64.tar.gz \
    && tar xfz /tmp/node.tar.gz -C /tmp/node --strip-components 1 \
    && ln -sf /tmp/node/bin/node /usr/bin/node \
    && ln -sf /tmp/node/bin/npm /usr/bin/npm
echo "=> NPM:$(npm --version||true) NODE:$(node --version||true)"
