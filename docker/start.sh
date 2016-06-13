#!/bin/bash

./manage.py build_solr_schema > /tmp/schema.xml
cp /tmp/schema.xml /apache-solr-3.6.2/example/solr/conf/
cp /apache-solr-3.6.2/example/solr/conf/stopwords.txt /apache-solr-3.6.2/example/solr/conf/stopwords_en.txt
export PATH=$PATH:/apache-solr-3.6.2/example/solr/conf/

assetgen --profile dev assetgen.yaml --force
./manage.py collectstatic --noinput
./manage.py migrate --noinput

# development: be logged in as specified REMOTE_USER
replaceinfile() {
    find $1 -type f -exec sed -i "s~$2~$3~g" {} \;
}
if [[ -n "$REMOTE_USER" ]]; then
    replaceinfile "/etc/supervisor/conf.d/supervisord.conf" "#devuser" "environment=REMOTE_USER=\"$REMOTE_USER\""
fi
# DEBUG
if [[ "$DEBUG" == "true" ]]; then
    FUM_CMD="command=./manage.py runserver --nostatic 8001"
    cp docker/dev_nginx.conf /etc/nginx/nginx.conf
else
    FUM_CMD="command=/usr/local/bin/uwsgi -s 127.0.0.1:3031 --wsgi-file uwsgi.py"
fi
replaceinfile "/etc/supervisor/conf.d/supervisord.conf" "#fumcmd" "$FUM_CMD"

/usr/bin/supervisord -c /etc/supervisor/supervisord.conf
