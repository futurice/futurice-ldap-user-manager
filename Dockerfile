FROM ubuntu:latest

COPY . /

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf


### APT-GET ###

RUN apt-get update
RUN apt-get install -y \
	build-essential htop \
	python-dev python-pip python-virtualenv \
	libxml2-dev libxslt1-dev \
	libcurl4-openssl-dev libssl-dev zlib1g-dev libpcre3-dev \
	libldap2-dev libsasl2-dev \
	libjpeg-dev \
	libfreetype6-dev \
	postgresql libpq-dev \
	npm \
	memcached \
	supervisor

RUN ln -s /usr/bin/nodejs /usr/bin/node


### DEPENDENCIES ### 

RUN apt-get install -y libffi-dev && pip install -r requirements.txt
RUN npm install


### POSTGRES ####

RUN mkdir -p media/portraits/full media/portraits/thumb media/portraits/badge
USER postgres
RUN /etc/init.d/postgresql start &&\
	psql --command 'CREATE USER root;' &&\
    createdb -O root fum
USER root
RUN /etc/init.d/postgresql start &&\
	./manage.py migrate --noinput &&\
	./manage.py datamigrate &&\
	./manage.py collectstatic --noinput


### SOLR ###




###



EXPOSE 8000

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf"]
