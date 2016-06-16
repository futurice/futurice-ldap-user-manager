#!/bin/bash

/etc/init.d/postgresql start &&\
	./manage.py migrate --noinput &&\
	./manage.py datamigrate &&\
	./manage.py collectstatic --noinput

/etc/init.d/postgresql stop

/usr/bin/supervisord -c /etc/supervisor/supervisord.conf