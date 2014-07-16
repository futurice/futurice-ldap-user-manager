# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'Users.active_in_planmill_tmp'
        db.delete_column(u'fum_users', 'active_in_planmill_tmp')


    def backwards(self, orm):
        # Adding field 'Users.active_in_planmill_tmp'
        db.add_column(u'fum_users', 'active_in_planmill_tmp',
                      self.gf('django.db.models.fields.IntegerField')(default=0),
                      keep_default=False)


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
            'active_in_planmill': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']", 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'null': 'True', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '500', 'null': 'True', 'blank': 'True'}),
            'google_status': ('django.db.models.fields.CharField', [], {'default': "'undefined'", 'max_length': '255'}),
            'home_directory': ('django.db.models.fields.CharField', [], {'max_length': '300', 'null': 'True', 'blank': 'True'}),
            'hr_number': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
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
            'shadow_last_change': ('django.db.models.fields.IntegerField', [], {'default': '16141', 'null': 'True', 'blank': 'True'}),
            'shadow_max': ('django.db.models.fields.IntegerField', [], {'default': '365', 'null': 'True', 'blank': 'True'}),
            'skype': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'supervisor': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['fum.Users']", 'null': 'True', 'blank': 'True'}),
            'suspended_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '500', 'null': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '24'})
        }
    }

    complete_apps = ['fum']