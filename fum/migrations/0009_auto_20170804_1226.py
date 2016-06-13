# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('fum', '0008_auto_20170804_1114'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='emails',
            unique_together=set([]),
        ),
    ]
