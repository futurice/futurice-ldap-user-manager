from django.conf import settings
import json, os, logging

GENERATED_ASSETS = {}
def read_assets():
    global GENERATED_ASSETS
    try:
        path = os.path.join(settings.PROJECT_ROOT, 'assets.json')
        GENERATED_ASSETS = json.loads(open(path).read())
    except IOError, e:
        logging.debug("ASSETS NOT CREATED: %s" % e)
        GENERATED_ASSETS = {}

def assets(value):
    if not GENERATED_ASSETS or (GENERATED_ASSETS and settings.DEBUG): # always refresh in DEBUG-mode
        read_assets()
    path = GENERATED_ASSETS[value]
    if value.endswith('.css'):
        return '<link href="%s%s" rel="stylesheet" type="text/css" />' % (settings.STATIC_URL, path)
    if value.endswith('.js'):
        return '<script type="text/javascript" src="%s%s" charset="utf-8"></script>' % (settings.STATIC_URL, path)
