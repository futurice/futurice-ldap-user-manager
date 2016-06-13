FROM fum

RUN cp local_settings.py.template local_settings.py
RUN sed -i local_settings.py \
    -e "s/^SECRET_KEY =.*$/SECRET_KEY = 'test'/" \
    -e "s/company/futurice/g" \
    -e "s/Company/Futurice/g" \
    -e 's/example\.com/futurice.com/g'

CMD python manage.py test --settings=fum.settings.test --noinput fum