# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('fum', '0003_users_portrait_badge_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='users',
            name='github',
            field=models.CharField(max_length=100, blank=True),
            preserve_default=True,
        ),
    ]
