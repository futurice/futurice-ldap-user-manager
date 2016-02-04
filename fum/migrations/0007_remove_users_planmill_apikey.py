# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('fum', '0006_auto_20151210_1152'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='users',
            name='planmill_apikey',
        ),
    ]
