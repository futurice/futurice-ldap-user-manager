FROM ubuntu:16.04
MAINTAINER Topi Paavilainen <topi.paavilainen@futurice.com>

### APT-GET ###

RUN apt-get update
RUN apt-get install -y \
	build-essential htop \
	python-dev python-pip \
	libxml2-dev libxslt1-dev \
	libcurl4-openssl-dev libssl-dev zlib1g-dev libpcre3-dev \
	libldap2-dev libsasl2-dev \
	libjpeg-dev \
	libfreetype6-dev \
	libpq-dev \
	npm \
	memcached \
	openjdk-8-jdk \
    nginx \
	supervisor

RUN ln -s /usr/bin/nodejs /usr/bin/node

RUN apt-get install -y wget unzip
RUN wget -q http://archive.apache.org/dist/lucene/solr/3.6.2/apache-solr-3.6.2.zip
RUN unzip apache-solr-3.6.2.zip

WORKDIR /opt/app

### DEPENDENCIES ### 
COPY package.json /opt/
RUN cd /opt/ && npm install
RUN ln -s /opt/node_modules/less/bin/lessc /usr/bin/

COPY requirements.txt /opt/app/
RUN apt-get install -y libffi-dev && pip install -r requirements.txt

COPY . /opt/app/

RUN mkdir -p media/portraits/full media/portraits/thumb media/portraits/badge

RUN mkdir /opt/static/ && mkdir /opt/media/

USER root
ENV DJANGO_SETTINGS_MODULE fum.settings.base
ENV SECRET_KEY default_insecure_secret

EXPOSE 8000
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
ADD docker/nginx.conf /etc/nginx/nginx.conf

CMD ["bash", "docker/start.sh"]
