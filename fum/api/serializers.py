from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.contrib.contenttypes.models import ContentType

from rest_framework import serializers, pagination
from rest_framework.parsers import JSONParser
from rest_framework.compat import smart_text

from fum.models import (
    Users, Groups, Servers, Projects, EMails, Resource, EMailAliases, SSHKey,
    get_generic_email,
)
from fum.common.middleware import get_current_request

import StringIO
import logging
from pprint import pprint as pp

log = logging.getLogger(__name__)

class QueryFieldsMixin(object):
    def get_fields(self, *args, **kwargs):
        fields = super(QueryFieldsMixin, self).get_fields(*args, **kwargs)
        request = get_current_request()
        if request and request.GET.get('fields'):
            fields = {k:v for k,v in fields.iteritems() if k in request.GET.get('fields')} or fields
        return fields

class GenericRelationModelManager(QueryFieldsMixin, serializers.ModelSerializer):
    def save_object(self, obj, **kwargs):
        """
        Save the deserialized object and return it.
        """
        obj.save(**kwargs)

        if getattr(obj, '_m2m_data', None):
            for accessor_name, object_list in obj._m2m_data.items():
                # setting a GenericRelation causes it to be cleared (!), which happens BEFORE validation.
                if accessor_name == 'email': # TODO: how to check for GenericRelation?
                    rel = getattr(obj, accessor_name)
                    if object_list:
                        rel.add(object_list[0])
                    else:
                        rel.all().delete() # .clear() not supported yet
                else:
                    setattr(obj, accessor_name, object_list)
            del(obj._m2m_data)

        if getattr(obj, '_related_data', None):
            for accessor_name, related in obj._related_data.items():
                setattr(obj, accessor_name, related)
            del(obj._related_data)

class EmailField(serializers.RelatedField):
    read_only = False

    def field_from_native(self, data, files, field_name, into):
        # When no email is provided, it it set to None, which is not a valid GenericRelation operation
        value = data.get(field_name, None)
        if value is not None:
            super(EmailField, self).field_from_native(data, files, field_name, into)

    def to_native(self, value):
        # Mimic a One-To-One GenericRelation
        email = get_generic_email(value)
        result = email.address if email else None
        return result

    def from_native(self, data):
        if self.parent.object:
            email = EMails(address=data, content_object=self.parent.object)
        else:
            email = EMails(address=data)
        result = [email]
        return result
    
class ResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resource
        fields = ('id', 'name', 'url')

#
# Users
#
class UsersSerializer(GenericRelationModelManager):
    email = EmailField(many=False, required=False)
    email_aliases = serializers.Field(source='email_aliases')
    portrait_full_url= serializers.Field(source='portrait_full_url')
    portrait_thumb_url= serializers.Field(source='portrait_thumb_url')
    portrait_badge_url = serializers.Field(source='portrait_badge_url')
    suspended_date = serializers.DateField(format="%Y-%m-%d", input_formats=["%Y-%m-%d"], required=False)
    password_expiration_date = serializers.Field(source='password_expires_date')
    password_changed_date = serializers.Field(source='password_changed_date')
    status = serializers.Field(source='get_status')

    class Meta:
        model = Users
        fields = ('id','first_name', 'last_name', 'username', 'title', 'phone1', 'phone2', 'email', 'github', 'skype',
                'physical_office', 'google_status', 'email_aliases', 'portrait_full_url', 'portrait_thumb_url', 'portrait_badge_url',
                'home_directory', 'suspended_date', 'supervisor', 'hr_number','password_expiration_date',
                'active_in_planmill','password_changed_date','status','flowdock_uid','planmill_uid',)

class UsersListSerializer(GenericRelationModelManager):
    portrait_full_url= serializers.Field(source='portrait_full_url')
    portrait_thumb_url= serializers.Field(source='portrait_thumb_url')
    portrait_badge_url = serializers.Field(source='portrait_badge_url')
    suspended_date = serializers.DateField(format="%Y-%m-%d", input_formats=["%Y-%m-%d"], required=False)
    password_expiration_date = serializers.Field(source='password_expires_date')
    password_changed_date = serializers.Field(source='password_changed_date')
    email = EmailField(many=False, required=False)
    status = serializers.Field(source='get_status')

    class Meta:
        model = Users
        fields = ('id', 'first_name', 'last_name', 'username', 'physical_office', 'email','suspended_date',
                'hr_number','password_expiration_date','active_in_planmill','password_changed_date',
                'portrait_thumb_url','portrait_full_url','portrait_badge_url',
                'status','flowdock_uid','planmill_uid',)

class PaginatedUsersSerializer(pagination.PaginationSerializer):
    class Meta:
        object_serializer_class = UsersSerializer

#
# Groups
#
class GroupsSerializer(GenericRelationModelManager):
    resources = serializers.RelatedField(many=True, source='resources')
    users = serializers.SlugRelatedField(many=True, read_only=True, slug_field='username')
    email = EmailField(many=False, required=False)
    email_aliases = serializers.Field(source='email_aliases')
    editor_group = serializers.SlugRelatedField(slug_field='name', required=False)
    
    class Meta:
        model = Groups
        fields = ('id', 'name', 'description', 'email', 'email_aliases', 'editor_group', 'users','resources')

class GroupsListSerializer(GenericRelationModelManager):
    class Meta:
        model = Groups
        fields = ('id', 'name', 'description')

class PaginatedGroupsSerializer(pagination.PaginationSerializer):
    class Meta:
        object_serializer_class = GroupsSerializer

#
# Servers
#
class ServersSerializer(GenericRelationModelManager):
    users = serializers.SlugRelatedField(many=True, read_only=True, slug_field='username')
    sudoers = serializers.SlugRelatedField(many=True, read_only=True, slug_field='username')
    email = EmailField(many=False, required=False)
    email_aliases = serializers.Field(source='email_aliases')
    editor_group = serializers.SlugRelatedField(slug_field='name', required=False)

    class Meta:
        model = Servers
        fields = ('id', 'name', 'description', 'email', 'email_aliases', 'editor_group', 'users', 'sudoers')

class ServersListSerializer(GenericRelationModelManager):
    class Meta:
        model = Servers
        fields = ('id', 'name', 'description')

class PaginatedServersSerializer(pagination.PaginationSerializer):
    class Meta:
        object_serializer_class = ServersSerializer

# 
# Projects
#
class ProjectsSerializer(GenericRelationModelManager):
    users = serializers.SlugRelatedField(many=True, read_only=True, slug_field='username')
    email = EmailField(many=False, required=False)
    email_aliases = serializers.Field(source='email_aliases')
    editor_group = serializers.SlugRelatedField(slug_field='name', required=False)

    class Meta:
        model = Projects
        fields = ('id', 'name', 'description', 'email', 'email_aliases', 'editor_group', 'users')

class ProjectsListSerializer(GenericRelationModelManager):
    class Meta:
        model = Projects
        fields = ('id', 'name', 'description')

class PaginatedProjectsSerializer(pagination.PaginationSerializer):
    class Meta:
        object_serializer_class = ProjectsSerializer


#
# Emails
#
class EMailsSerializer(serializers.ModelSerializer):

    class Meta:
        model = EMails
        fields = ('id', 'address',)

#
# Aliases
#
class AliasesSerializer(serializers.ModelSerializer):
    parent = serializers.Field(source='parent')

    class Meta:
        model = EMailAliases
        fields = ('id', 'address', 'parent')

#
# SSH Keys
#
class SSHKeysSerializer(serializers.ModelSerializer):

    user = serializers.SlugRelatedField(slug_field='username',
            read_only=True)

    class Meta:
        model = SSHKey
        fields = ('title', 'key', 'user', 'fingerprint', 'bits')
