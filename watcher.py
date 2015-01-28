#! /usr/bin/env python

from django.conf import settings
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

import datetime
import time, logging, subprocess, os

logging.basicConfig(level=logging.INFO)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fum.settings.base")

BLACKLIST = ['/.git','.git','.log','dist/','logs/','/tests','.db', settings.MEDIA_ROOT.rstrip('/'), settings.STATIC_ROOT.rstrip('/'),]
def blacklisted(path):
    return any(black in path for black in BLACKLIST)

def update_urls():
    command = 'python manage.py js_urls'
    try:
        output = subprocess.check_output(command.split())
    except Exception, e:
        print e

LAST_RUN = datetime.datetime.now()
def is_time_to_run_again(interval=2):
    global LAST_RUN
    now = datetime.datetime.now()
    diff = (now-LAST_RUN).total_seconds()
    r = diff > interval
    if r:
        LAST_RUN = now
    return r

class CollectStaticHandler(FileSystemEventHandler):
    def prepare_system(self, event):
        if not blacklisted(event.src_path):
            if not is_time_to_run_again() and 'WARMUP' not in event.src_path:
                return
            print ":>", event.src_path
            update_urls()
            command = 'assetgen --profile dev assetgen.yaml'
            try:
                output = subprocess.check_output(command.split())
            except Exception, e:
                print e
    def on_moved(self, event):
        what = 'directory' if event.is_directory else 'file'
        self.prepare_system(event)
    def on_created(self, event):
        what = 'directory' if event.is_directory else 'file'
        self.prepare_system(event)
    def on_deleted(self, event):
        what = 'directory' if event.is_directory else 'file'
        self.prepare_system(event)
    def on_modified(self, event):
        what = 'directory' if event.is_directory else 'file'
        self.prepare_system(event)

if __name__ == "__main__":
    print "Watcher Online."

    # Ensure we're not in an invalid state. assetgen keeps state in /tmp
    # which tells it not to generate e.g. assets.json next time you run it.
    # If you deleted assets.json, the werserver will serve errors and you
    # won't be able to fix this even by cleaning and rebuilding the entire
    # repository: because assetgen's /tmp state tells it not to rebuild
    # assets.json.
    #
    # 'assetgen --nuke' would be better but it also deletes the work done by
    # 'manage.py collectstatic'.
    subprocess.check_call(['assetgen', '--force',
        '--profile', 'dev', 'assetgen.yaml'])

    observer = Observer()
    observer.schedule(CollectStaticHandler(), path='.', recursive=True)

    # run once, to catchup on any changes while offline
    CollectStaticHandler().prepare_system( type('Event', (object,), {'src_path': 'INITIAL/WARMUP/REQUEST'}) )

    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
