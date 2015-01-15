# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import fum.common.mixins
import datetime
import fum.common.fields
import fum.models


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='EMailAliases',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('address', models.EmailField(unique=True, max_length=254)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model, fum.common.mixins.DirtyFieldsMixin),
        ),
        migrations.CreateModel(
            name='EMails',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('address', models.EmailField(unique=True, max_length=254, blank=True)),
                ('object_id', models.PositiveIntegerField(null=True)),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType')),
            ],
            options={
            },
            bases=(models.Model, fum.common.mixins.DirtyFieldsMixin),
        ),
        migrations.CreateModel(
            name='Groups',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('object_id', models.PositiveIntegerField(null=True, editable=False, blank=True)),
                ('name', models.CharField(unique=True, max_length=500)),
                ('description', models.CharField(default=b'', max_length=5000, blank=True)),
                ('created', models.DateTimeField(default=datetime.datetime.now, null=True, blank=True)),
                ('content_type', models.ForeignKey(blank=True, editable=False, to='contenttypes.ContentType', null=True)),
                ('editor_group', models.ForeignKey(blank=True, to='fum.Groups', null=True)),
            ],
            options={
                'ordering': ['name'],
                'abstract': False,
            },
            bases=(models.Model, fum.common.mixins.DirtyFieldsMixin),
        ),
        migrations.CreateModel(
            name='Projects',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('object_id', models.PositiveIntegerField(null=True, editable=False, blank=True)),
                ('name', models.CharField(unique=True, max_length=500)),
                ('description', models.CharField(default=b'', max_length=5000, blank=True)),
                ('created', models.DateTimeField(default=datetime.datetime.now, null=True, blank=True)),
                ('content_type', models.ForeignKey(blank=True, editable=False, to='contenttypes.ContentType', null=True)),
                ('editor_group', models.ForeignKey(blank=True, to='fum.Groups', null=True)),
            ],
            options={
                'ordering': ['name'],
                'abstract': False,
            },
            bases=(models.Model, fum.common.mixins.DirtyFieldsMixin),
        ),
        migrations.CreateModel(
            name='Resource',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=500)),
                ('url', models.URLField(max_length=500)),
                ('archived', models.BooleanField(default=False)),
                ('object_id', models.PositiveIntegerField()),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model, fum.common.mixins.DirtyFieldsMixin),
        ),
        migrations.CreateModel(
            name='Servers',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('object_id', models.PositiveIntegerField(null=True, editable=False, blank=True)),
                ('name', models.CharField(unique=True, max_length=500)),
                ('description', models.CharField(default=b'', max_length=5000, blank=True)),
                ('created', models.DateTimeField(default=datetime.datetime.now, null=True, blank=True)),
                ('content_type', models.ForeignKey(blank=True, editable=False, to='contenttypes.ContentType', null=True)),
                ('editor_group', models.ForeignKey(blank=True, to='fum.Groups', null=True)),
            ],
            options={
                'ordering': ['name'],
                'abstract': False,
            },
            bases=(models.Model, fum.common.mixins.DirtyFieldsMixin),
        ),
        migrations.CreateModel(
            name='SSHKey',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=50)),
                ('key', models.TextField()),
                ('fingerprint', models.CharField(unique=True, max_length=100, db_index=True)),
                ('bits', models.IntegerField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Users',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('object_id', models.PositiveIntegerField(null=True, editable=False, blank=True)),
                ('first_name', models.CharField(max_length=500, null=True, blank=True)),
                ('last_name', models.CharField(max_length=500)),
                ('username', models.CharField(unique=True, max_length=24)),
                ('title', models.CharField(max_length=500, null=True, blank=True)),
                ('phone1', models.CharField(max_length=100, null=True, blank=True)),
                ('phone2', models.CharField(max_length=100, null=True, blank=True)),
                ('skype', models.CharField(max_length=100, null=True, blank=True)),
                ('physical_office', models.CharField(max_length=100, null=True, blank=True)),
                ('google_status', models.CharField(default=b'undefined', max_length=255, choices=[(b'undefined', b'undefined'), (b'activeperson', b'activeperson'), (b'activemachine', b'activemachine'), (b'suspended', b'suspended'), (b'deleted', b'deleted')])),
                ('picture_uploaded_date', models.DateTimeField(null=True, editable=False, blank=True)),
                ('suspended_date', models.DateTimeField(null=True, blank=True)),
                ('publickey', models.TextField(null=True, blank=True)),
                ('shadow_last_change', models.IntegerField(default=fum.models.shadow_initial, null=True, editable=False, blank=True)),
                ('shadow_max', models.IntegerField(default=fum.models.calculate_password_valid_days, null=True, editable=False, blank=True)),
                ('portrait_thumb_name', models.CharField(max_length=500, null=True, blank=True)),
                ('portrait_full_name', models.CharField(max_length=500, null=True, blank=True)),
                ('home_directory', models.CharField(max_length=300, null=True, blank=True)),
                ('created', models.DateTimeField(default=datetime.datetime.now, null=True, blank=True)),
                ('hr_number', models.CharField(max_length=255, null=True, blank=True)),
                ('active_in_planmill', models.IntegerField(default=0, choices=[(0, b'Disabled'), (1, b'Active'), (2, b'Inactive')])),
                ('content_type', models.ForeignKey(blank=True, editable=False, to='contenttypes.ContentType', null=True)),
                ('supervisor', models.ForeignKey(blank=True, to='fum.Users', null=True)),
            ],
            options={
                'ordering': ['first_name', 'last_name'],
            },
            bases=(models.Model, fum.common.mixins.DirtyFieldsMixin),
        ),
        migrations.AddField(
            model_name='sshkey',
            name='user',
            field=models.ForeignKey(to='fum.Users'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='servers',
            name='sudoers',
            field=fum.common.fields.SudoersManyField(to='fum.Users', null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='servers',
            name='users',
            field=fum.common.fields.UsersManyField(related_name=b'fum_servers', null=True, to='fum.Users', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='projects',
            name='users',
            field=fum.common.fields.UsersManyField(related_name=b'fum_projects', null=True, to='fum.Users', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='groups',
            name='users',
            field=fum.common.fields.UsersManyField(related_name=b'fum_groups', null=True, to='fum.Users', blank=True),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='emails',
            unique_together=set([('content_type', 'object_id')]),
        ),
        migrations.AddField(
            model_name='emailaliases',
            name='parent',
            field=models.ForeignKey(to='fum.EMails'),
            preserve_default=True,
        ),
    ]
