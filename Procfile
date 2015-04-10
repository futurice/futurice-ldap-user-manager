# All processes to develop FUM locally
# Configure own settings in another file
# PROCFILE=Procfile.dev OR procboy -e Procfile.dev
>django-migrate: python manage.py migrate --noinput
django: python manage.py runserver --nostatic --traceback
watcher: python watcher.py
