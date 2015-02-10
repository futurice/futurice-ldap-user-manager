# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('fum', '0002_auto_20150122_1308'),
    ]

    operations = [
        migrations.AddField(
            model_name='users',
            name='portrait_badge_name',
            field=models.CharField(max_length=500, null=True, blank=True),
            preserve_default=True,
        ),
    ]
