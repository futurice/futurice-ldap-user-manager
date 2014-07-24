INSTALL
=======

```
apt-get install build-essential python-setuptools python-dev libldap2-dev libsasl2-dev libssl-dev libxslt1-dev
pip install --allow-external PIL --allow-unverified PIL -r requirements.txt
npm install

cp local_settings.py.template local_settings.py

# Edit LDAP configuration.
createdb fum	# If using PostgreSQL

./manage.py syncdb --noinput
./manage.py migrate
./manage.py datamigrate

./manage.py collectstatic --noinput	# rest_framework css/js

PATH=./node_modules/.bin:$PATH ./watcher.py	# LESS/JS bunding, and moving of APP/static to /static
REMOTE_USER=x ./manage.py runserver --nostatic
```

Testing: 

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
