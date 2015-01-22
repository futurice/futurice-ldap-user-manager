# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('fum', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='groups',
            name='created',
            field=models.DateTimeField(default=django.utils.timezone.now, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='projects',
            name='created',
            field=models.DateTimeField(default=django.utils.timezone.now, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='servers',
            name='created',
            field=models.DateTimeField(default=django.utils.timezone.now, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='users',
            name='created',
            field=models.DateTimeField(default=django.utils.timezone.now, null=True, blank=True),
            preserve_default=True,
        ),
    ]
