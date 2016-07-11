FROM ubuntu:16.04
MAINTAINER Topi Paavilainen <topi.paavilainen@futurice.com>

WORKDIR /opt/app


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
	openjdk-8-jdk \
	supervisor

RUN ln -s /usr/bin/nodejs /usr/bin/node

RUN apt-get install -y wget unzip
RUN wget -q http://archive.apache.org/dist/lucene/solr/3.6.2/apache-solr-3.6.2.zip
RUN unzip apache-solr-3.6.2.zip

### DEPENDENCIES ### 

COPY requirements.txt /opt/app/
RUN apt-get install -y libffi-dev && pip install -r requirements.txt

COPY . /opt/app/
RUN npm install && ln -s /opt/app/node_modules/less/bin/lessc /usr/bin/

### POSTGRES ###

RUN mkdir -p media/portraits/full media/portraits/thumb media/portraits/badge
USER postgres
RUN /etc/init.d/postgresql start &&\
	psql --command 'CREATE USER root;' &&\
    createdb -O root fum
USER root


### SOLR ###

RUN ./manage.py build_solr_schema > schema.xml
RUN cp schema.xml apache-solr-3.6.2/example/solr/conf/
RUN cp apache-solr-3.6.2/example/solr/conf/stopwords.txt apache-solr-3.6.2/example/solr/conf/stopwords_en.txt
RUN export PATH=$PATH:/apache-solr-3.6.2/example/solr/conf/


EXPOSE 8000
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

CMD ["bash", "docker/start.sh"]