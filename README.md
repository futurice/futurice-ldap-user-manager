[![Build Status](https://travis-ci.org/futurice/futurice-ldap-user-manager.svg?branch=master)](https://travis-ci.org/futurice/futurice-ldap-user-manager)

DESCRIPTION
===========
**FUM** is an user management system for LDAP (Lightweight Directory Access Protocol). FUM makes it easy to handle information about your employees, their projects and servers they have access to. LDAP is a good protocol for user management, but it needs an user-friendly layer on top of it. One of the strengths of FUM is that it gives the users a lot of freedom over their data.

BACKGROUND
==========
**FUM** was created as an internal support system at [Futurice](http://www.futurice.com). It was open sourced as a part of the [Summer of Love](http://blog.futurice.com/summer-of-love-of-open-source) program.

SETUP
=====
```bash
sed -e "s/^SECRET_KEY =.*$/SECRET_KEY = 'test'/" \
    -e "s/company/futurice/g" \
    -e "s/Company/Futurice/g" \
    -e 's/example\.com/futurice.com/g' \
    local_settings.py.template >local_settings.py

# Fill in the LDAP_CONNECTION fields
# set USE_TLS=False if some LDAP connections don't work
# Change IT_TEAM to an existing group you're part of to get SUDO permission
```
Run using Docker
================
First build & run your local 389 ldap-server on docker. Insert your 389-servers IP address to `local_settings.py > LDAP_CONNECTION > uri`. 389-server should be running while building FUM. 
Set `USE_TLS` and `CHANGES_SOCKET_ENABLED` in `settings/base.py` to False.

Build the docker image:
```
docker build -t fum-docker futurice-ldap-user-manager/
```

Run:
```
docker run -p 8080:8000 fum-docker
```

Now FUM should be running locally and can be viewed on `localhost:8080`

To search with Solr+Haystack:
````
docker exec <fum container name> ./manage.py update_index
````

Running tests:
```
docker exec <fum container name> ./manage.py test --settings=fum.settings.test_live
```
FUM should be running while running tests.



Develop locally using Procboy
=============================

Setup, and **configure** processes and environment:
cp Procfile.template Procfile
cp env.template .env

Prepare dependencies (preferably in a virtualenv[1]):
```
pip install -r requirements.txt
npm install
```

Run the project:
```
procboy
```
View [localhost:8000](http://localhost:8000)


INSTALL
=======

```
apt-get install build-essential python-setuptools python-dev libldap2-dev libsasl2-dev libssl-dev libxslt1-dev
pip install -r requirements.txt
npm install

mkdir -p media/portraits/full media/portraits/thumb media/portraits/badge

# Edit LDAP configuration.
createdb fum	# If using PostgreSQL

./manage.py migrate --noinput
./manage.py datamigrate

./manage.py collectstatic --noinput	# rest_framework css/js

PATH=./node_modules/.bin:$PATH ./watcher.py	# LESS/JS bunding, and moving of APP/static to /static
REMOTE_USER=x ./manage.py runserver --nostatic
```

Testing: 

You should have `memcached` running when running tests.
`python manage.py test --settings=fum.settings.test`

SEARCH (Haystack + SOLR)
========================

get solr and unzip:

```
wget http://www.nic.funet.fi/pub/mirrors/apache.org/lucene/solr/3.6.2/apache-solr-3.6.2.zip
unzip apache-solr-3.6.2.zip
```

update solr schema:

```
python manage.py build_solr_schema > schema.xml
```

drop the schema to solr's conf folder:

```
cp schema.xml apache-solr-3.6.2/example/solr/conf/
```

create stopwords_en.txt:

```
cp apache-solr-3.6.2/example/solr/conf/stopwords.txt apache-solr-3.6.2/example/solr/conf/stopwords_en.txt
```

add the schema location to you PATH:

```
export PATH=$PATH:/../../apache-solr-3.6.2/example/solr/conf/
```

start solr:

```
java -jar /apache-solr-3.6.2/example/start.jar
```

update indexes:

```
python ./manage.py update_index
```

and start searching.


DEPLOY
======

```
fab production <COMMAND>
 deploy
 reset_and_sync
```

PRODUCTION SERVER SETUP
=======================

```
apt-get install \
build-essential python-setuptools python-dev \
git git-core curl \
libxml2-dev libxslt1-dev \
libcurl4-openssl-dev libssl-dev zlib1g-dev libpcre3-dev \
libldap2-dev libsasl2-dev \
libjpeg-dev

# link libjpeg so that PIL can find it
ln -s /usr/lib/x86_64-linux-gnu/libjpeg.so /usr/lib
ln -s /usr/lib/x86_64-linux-gnu/libfreetype.so /usr/lib
ln -s /usr/lib/x86_64-linux-gnu/libz.so /usr/lib

# reinstall PIL
pip install -I PIL

# nodejs
apt-get update
apt-get install python-software-properties python g++ make
add-apt-repository ppa:chris-lea/node.js
apt-get update
apt-get install nodejs
```

CRON REMINDERS
==============

Check for expiring passwords:

```
python manage.py remind (--dry-run)
```

This should be ran once a day and sends a reminder at 30 days, 2 weeks and every day for the last week.
A final notice is sent once the password has expired.


TROUBLESHOOTING
================

If you're getting "No more space on device" errors when running the watcher.py on Ubuntu, you might need to set the ulimits: http://posidev.com/blog/2009/06/04/set-ulimit-parameters-on-ubuntu/ or run this magic command:

```bash
echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf && sudo sysctl -p
```

SCREENSHOTS
===========
![Profile view from FUM.](http://i.imgur.com/LAhfMml.png)

ABOUT FUTURICE
==============
[Futurice](http://www.futurice.com) is a lean service creation company with offices in Helsinki, Tampere, Berlin and London.

People who have contributed to FUM:
- [Jussi Vaihia](https://github.com/mixman)
- [Oskar Ehnström](https://github.com/Ozzee)
- [Sébastien Piquemal](https://github.com/sebpiq)
- [Markus Koskinen](https://github.com/mkoskinen)
- [Henri Holopainen](https://github.com/henriholopainen)
- [Boyan Tabakov](https://github.com/bladealslayer)
- [Olli Jarva](https://github.com/ojarva)
- [Ville Tainio](https://github.com/Wisheri)

SUPPORT
=======
Pull requests and new issues are of course welcome. If you have any questions, comments or feedback you can contact us by email at sol@futurice.com. We will try to answer your questions, but we have limited manpower so please, be patient with us.


FOOTNOTES
=========
[1] [virtualenv](https://virtualenv.pypa.io/en/latest/) installation:
```
sudo pip install virtualenv
mkvirtualenv fum
source fum/bin/activate
```
