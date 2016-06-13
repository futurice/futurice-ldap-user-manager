# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('fum', '0007_remove_users_planmill_apikey'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='emailaliases',
            name='parent',
        ),
        migrations.DeleteModel(
            name='EMailAliases',
        ),
        migrations.AddField(
            model_name='emails',
            name='alias_for',
            field=models.ForeignKey(blank=True, to='fum.EMails', null=True),
            preserve_default=True,
        ),
    ]
