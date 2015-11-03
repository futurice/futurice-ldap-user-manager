# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('fum', '0004_users_github'),
    ]

    operations = [
        migrations.AddField(
            model_name='users',
            name='flowdock_uid',
            field=models.IntegerField(null=True, blank=True),
            preserve_default=True,
        ),
    ]
