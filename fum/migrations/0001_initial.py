# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Users'
        db.create_table(u'fum_users', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'], null=True, blank=True)),
            ('object_id', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
            ('first_name', self.gf('django.db.models.fields.CharField')(max_length=500, null=True, blank=True)),
            ('last_name', self.gf('django.db.models.fields.CharField')(max_length=500)),
            ('username', self.gf('django.db.models.fields.CharField')(unique=True, max_length=24)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=500, null=True, blank=True)),
            ('phone1', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('phone2', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('skype', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('physical_office', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('google_status', self.gf('django.db.models.fields.CharField')(default='0', max_length=1)),
            ('picture_uploaded_date', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('suspended_date', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('publickey', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('shadow_last_change', self.gf('django.db.models.fields.IntegerField')(default=16000, null=True, blank=True)),
            ('shadow_max', self.gf('django.db.models.fields.IntegerField')(default=365, null=True, blank=True)),
            ('portrait_thumb_name', self.gf('django.db.models.fields.CharField')(max_length=500, null=True, blank=True)),
            ('portrait_full_name', self.gf('django.db.models.fields.CharField')(max_length=500, null=True, blank=True)),
            ('home_directory', self.gf('django.db.models.fields.CharField')(max_length=300, null=True, blank=True)),
        ))
        db.send_create_signal(u'fum', ['Users'])

        # Adding model 'Groups'
        db.create_table(u'fum_groups', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'], null=True, blank=True)),
            ('object_id', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=500)),
            ('description', self.gf('django.db.models.fields.CharField')(default='', max_length=5000, blank=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, null=True, blank=True)),
            ('editor_group', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['fum.Groups'], null=True, blank=True)),
        ))
        db.send_create_signal(u'fum', ['Groups'])

        # Adding M2M table for field users on 'Groups'
        m2m_table_name = db.shorten_name(u'fum_groups_users')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('groups', models.ForeignKey(orm[u'fum.groups'], null=False)),
            ('users', models.ForeignKey(orm[u'fum.users'], null=False))
        ))
        db.create_unique(m2m_table_name, ['groups_id', 'users_id'])

        # Adding model 'Servers'
        db.create_table(u'fum_servers', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'], null=True, blank=True)),
            ('object_id', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=500)),
            ('description', self.gf('django.db.models.fields.CharField')(default='', max_length=5000, blank=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, null=True, blank=True)),
            ('editor_group', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['fum.Groups'], null=True, blank=True)),
        ))
        db.send_create_signal(u'fum', ['Servers'])

        # Adding M2M table for field users on 'Servers'
        m2m_table_name = db.shorten_name(u'fum_servers_users')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('servers', models.ForeignKey(orm[u'fum.servers'], null=False)),
            ('users', models.ForeignKey(orm[u'fum.users'], null=False))
        ))
        db.create_unique(m2m_table_name, ['servers_id', 'users_id'])

        # Adding M2M table for field sudoers on 'Servers'
        m2m_table_name = db.shorten_name(u'fum_servers_sudoers')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('servers', models.ForeignKey(orm[u'fum.servers'], null=False)),
            ('users', models.ForeignKey(orm[u'fum.users'], null=False))
        ))
        db.create_unique(m2m_table_name, ['servers_id', 'users_id'])

        # Adding model 'Projects'
        db.create_table(u'fum_projects', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'], null=True, blank=True)),
            ('object_id', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=500)),
            ('description', self.gf('django.db.models.fields.CharField')(default='', max_length=5000, blank=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, null=True, blank=True)),
            ('editor_group', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['fum.Groups'], null=True, blank=True)),
        ))
        db.send_create_signal(u'fum', ['Projects'])

        # Adding M2M table for field users on 'Projects'
        m2m_table_name = db.shorten_name(u'fum_projects_users')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('projects', models.ForeignKey(orm[u'fum.projects'], null=False)),
            ('users', models.ForeignKey(orm[u'fum.users'], null=False))
        ))
        db.create_unique(m2m_table_name, ['projects_id', 'users_id'])

        # Adding model 'EMails'
        db.create_table(u'fum_emails', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('address', self.gf('django.db.models.fields.EmailField')(unique=True, max_length=254, blank=True)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'])),
            ('object_id', self.gf('django.db.models.fields.PositiveIntegerField')(null=True)),
        ))
        db.send_create_signal(u'fum', ['EMails'])

        # Adding unique constraint on 'EMails', fields ['content_type', 'object_id']
        db.create_unique(u'fum_emails', ['content_type_id', 'object_id'])

        # Adding model 'EMailAliases'
        db.create_table(u'fum_emailaliases', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('address', self.gf('django.db.models.fields.EmailField')(unique=True, max_length=254)),
            ('parent', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['fum.EMails'])),
        ))
        db.send_create_signal(u'fum', ['EMailAliases'])

        # Adding model 'Resource'
        db.create_table(u'fum_resource', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=500)),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=500)),
            ('archived', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'])),
            ('object_id', self.gf('django.db.models.fields.PositiveIntegerField')()),
        ))
        db.send_create_signal(u'fum', ['Resource'])

        # Adding model 'AuditLogs'
        db.create_table(u'fum_auditlogs', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('uid', self.gf('django.db.models.fields.IntegerField')(db_index=True, null=True, blank=True)),
            ('operation', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('timestamp', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('oid', self.gf('django.db.models.fields.IntegerField')(db_index=True, null=True, blank=True)),
            ('otype', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'], null=True, blank=True)),
            ('roid', self.gf('django.db.models.fields.IntegerField')(db_index=True, null=True, blank=True)),
            ('rotype', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='rotype', null=True, to=orm['contenttypes.ContentType'])),
        ))
        db.send_create_signal(u'fum', ['AuditLogs'])


    def backwards(self, orm):
        # Removing unique constraint on 'EMails', fields ['content_type', 'object_id']
        db.delete_unique(u'fum_emails', ['content_type_id', 'object_id'])

        # Deleting model 'Users'
        db.delete_table(u'fum_users')

        # Deleting model 'Groups'
        db.delete_table(u'fum_groups')

        # Removing M2M table for field users on 'Groups'
        db.delete_table(db.shorten_name(u'fum_groups_users'))

        # Deleting model 'Servers'
        db.delete_table(u'fum_servers')

        # Removing M2M table for field users on 'Servers'
        db.delete_table(db.shorten_name(u'fum_servers_users'))

        # Removing M2M table for field sudoers on 'Servers'
        db.delete_table(db.shorten_name(u'fum_servers_sudoers'))

        # Deleting model 'Projects'
        db.delete_table(u'fum_projects')

        # Removing M2M table for field users on 'Projects'
        db.delete_table(db.shorten_name(u'fum_projects_users'))

        # Deleting model 'EMails'
        db.delete_table(u'fum_emails')

        # Deleting model 'EMailAliases'
        db.delete_table(u'fum_emailaliases')

        # Deleting model 'Resource'
        db.delete_table(u'fum_resource')

        # Deleting model 'AuditLogs'
        db.delete_table(u'fum_auditlogs')


    models = {
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'fum.auditlogs': {
            'Meta': {'object_name': 'AuditLogs'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'oid': ('django.db.models.fields.IntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'operation': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'otype': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']", 'null': 'True', 'blank': 'True'}),
            'roid': ('django.db.models.fields.IntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'rotype': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'rotype'", 'null': 'True', 'to': u"orm['contenttypes.ContentType']"}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'uid': ('django.db.models.fields.IntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'})
        },
        u'fum.emailaliases': {
            'Meta': {'object_name': 'EMailAliases'},
            'address': ('django.db.models.fields.EmailField', [], {'unique': 'True', 'max_length': '254'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['fum.EMails']"})
        },
        u'fum.emails': {
            'Meta': {'unique_together': "(('content_type', 'object_id'),)", 'object_name': 'EMails'},
            'address': ('django.db.models.fields.EmailField', [], {'unique': 'True', 'max_length': '254', 'blank': 'True'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'})
        },
        u'fum.groups': {
            'Meta': {'ordering': "['name']", 'object_name': 'Groups'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']", 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '5000', 'blank': 'True'}),
            'editor_group': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['fum.Groups']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '500'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'users': ('fum.common.fields.UsersManyField', [], {'blank': 'True', 'related_name': "u'fum_groups'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['fum.Users']"})
        },
        u'fum.projects': {
            'Meta': {'ordering': "['name']", 'object_name': 'Projects'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']", 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '5000', 'blank': 'True'}),
            'editor_group': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['fum.Groups']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '500'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'users': ('fum.common.fields.UsersManyField', [], {'blank': 'True', 'related_name': "u'fum_projects'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['fum.Users']"})
        },
        u'fum.resource': {
            'Meta': {'object_name': 'Resource'},
            'archived': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        u'fum.servers': {
            'Meta': {'ordering': "['name']", 'object_name': 'Servers'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']", 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '5000', 'blank': 'True'}),
            'editor_group': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['fum.Groups']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '500'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'sudoers': ('fum.common.fields.SudoersManyField', [], {'symmetrical': 'False', 'to': u"orm['fum.Users']", 'null': 'True', 'blank': 'True'}),
            'users': ('fum.common.fields.UsersManyField', [], {'blank': 'True', 'related_name': "u'fum_servers'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['fum.Users']"})
        },
        u'fum.users': {
            'Meta': {'ordering': "['first_name', 'last_name']", 'object_name': 'Users'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']", 'null': 'True', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '500', 'null': 'True', 'blank': 'True'}),
            'google_status': ('django.db.models.fields.CharField', [], {'default': "'0'", 'max_length': '1'}),
            'home_directory': ('django.db.models.fields.CharField', [], {'max_length': '300', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'phone1': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'phone2': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'physical_office': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'picture_uploaded_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'portrait_full_name': ('django.db.models.fields.CharField', [], {'max_length': '500', 'null': 'True', 'blank': 'True'}),
            'portrait_thumb_name': ('django.db.models.fields.CharField', [], {'max_length': '500', 'null': 'True', 'blank': 'True'}),
            'publickey': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'shadow_last_change': ('django.db.models.fields.IntegerField', [], {'default': '16000', 'null': 'True', 'blank': 'True'}),
            'shadow_max': ('django.db.models.fields.IntegerField', [], {'default': '365', 'null': 'True', 'blank': 'True'}),
            'skype': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'suspended_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '500', 'null': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '24'})
        }
    }

    complete_apps = ['fum']