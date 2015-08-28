#coding:utf-8
from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError
from django.db.models import Max
from django.db import models, transaction
from django.db import IntegrityError
from django import forms
from django.utils.timezone import now
from django.utils import timezone

from dateutil.relativedelta import relativedelta
from datetime import datetime
from re import sub
from fnmatch import fnmatch
from ldap import modlist

import copy
import logging
import types
import json
import hashlib
import smbpasswd
import re
import sshpubkeys
import sys
import os

from ldap_helpers import to_ldap_value, fetch, ldap, ldap_cls, AttrDict

from fum.common.mixins import DirtyFieldsMixin
from fum.common.middleware import get_current_request
from fum.common.util import LazyDict, to_json, pretty_diff, random_ldap_password
from fum.common.fields import LdapManyToManyField, UsersManyField, SudoersManyField
from fum.util import get_project_models

from rest_framework.authtoken.models import Token

from pprint import pprint as pp

log = logging.getLogger(__name__)

WEEKDAY_FRIDAY = 4
EPOCH = datetime(1970, 1, 1, tzinfo=timezone.get_default_timezone())

def shadow_initial():
    return (now() - EPOCH).days

def calculate_password_valid_days():
    # Password valid for about 1 year
    t = now() + relativedelta(years=1)
    while t.weekday() > WEEKDAY_FRIDAY: # Don't let the expiration date be during the weekend
        t += relativedelta(days=1)
    return 1+(t - now()).days # We never get full days, so the +1 is for rounding error

def get_generic_email(email):
    if not isinstance(email, EMails):
        email = email.all()
        if email:
            return email[0]
        else:
            return None
    return email

class MotherManager(models.Manager):
    def get_or_create(self, **kwargs):
        if any(k in os.environ.get('DJANGO_SETTINGS_MODULE') for k in ['test','test_live']):
            from fum.common.ldap_test_suite import LdapFunctionality
            defaults = kwargs.pop('defaults', {})
            lf = LdapFunctionality()
            unique_field = self.model.get_by_name()
            created = False
            try:
                obj = self.model.objects.get(**kwargs)
            except self.model.DoesNotExist:
                kwargs.update(defaults)
                obj = lf.save_safe(self.model, kw=kwargs, lookup={unique_field: kwargs.get(unique_field)})
                created = True
            return obj, created
        else:
            return self.get_query_set().get_or_create(**kwargs)

class Mother(models.Model, DirtyFieldsMixin):
    ldap_only_fields = {}

    objects = MotherManager()

    @staticmethod
    def get_by_name():
        return 'name'

    def get_all_relations(self):
        r = {}
        for field,model in self._meta.get_m2m_with_model():
            r.update({field.name: field})
        for field,model in self._meta.get_all_related_objects_with_model():
            r.update({field.field.name: field.field})
        return r

    def get_absolute_name(self):
        return self.name

    def get_dn(self, parent, child):
        return parent.get_dn()

    ##
    ## START MODEL-VALIDATION
    ##

    def clean(self):
        super(Mother, self).clean()
        request = get_current_request()
        if not self.can_edit(request=request, instance=self):
            raise ValidationError('Permission denied')

    def delete(self, *args, **kwargs):
        request = get_current_request()
        if not self.can_delete(request):
            raise ValidationError('Permission denied')
        super(Mother, self).delete(*args, **kwargs)

    def can_edit(self, request, instance, child=None, field=None):
        actor = ActorPermission(
                instance=instance,
                request=request or get_current_request(),
                child=child,
                field=field,)
        actor.can_edit()
        return actor.has_permission()

    def can_delete(self, request=None, instance=None, child=None, field=None):
        actor = ActorPermission(
                instance=self,
                request=request or get_current_request(),)
        actor.can_delete()
        return actor.has_permission()

    def can_m2m_remove(self, request=None, instance=None, child=None, field=None):
        actor = ActorPermission(
                instance=instance,
                request=request or get_current_request(),
                child=child,
                field=field,)
        actor.can_m2m_remove()
        return actor.has_permission()


    ##
    ## END MODEL-VALIDATION
    ##

    class Meta:
        abstract = True

class LDAPModel(Mother):
    content_type = models.ForeignKey(ContentType, null=True, blank=True, editable=False)
    object_id = models.PositiveIntegerField(null=True, blank=True, editable=False)
    content_object = generic.GenericForeignKey('content_type', 'object_id')
    ldap_filter = "(objectClass=top)" # this is common to all objects, and we don't use objectclass to differentiate objects under a dn

    def __init__(self, *args, **kwargs):
        LDAP_CLASS = kwargs.pop('LDAP_CLASS', None)
        super(LDAPModel, self).__init__(*args, **kwargs)
        self.ldap = ldap_cls(parent=self, LDAP_CLASS=LDAP_CLASS)

    def __unicode__(self):
        return u'%s'%self.name

    class Meta:
        abstract = True

    def audit_url(self):
        return reverse('history-by-id', kwargs=dict(ct_id=self.get_content_type().pk, id=self.pk))

    def create_ldap_relations(self): # Servers requires SUDOErs, temporary fix until LdapForeignKeys
        pass

    def ldap_delete(self):
        self.ldap.delete() # deletes directly from LDAP, can remove values that are not in DB.

    def get_ldap_m2m_relations(self):
        r = []
        for field, model in self._meta.get_m2m_with_model():
            if isinstance(field, LdapManyToManyField):
                r.append(field)
        return r

    def get_dn(self):
        ldap_id_value = to_ldap_value(self.get_ldap_id_value())
        return '%s=%s,%s' % (self.ldap_id_field, ldap_id_value, self.ldap_base_dn)

    def ldap_attrs(self):
        tmp = []
        for k,v in self.ldap_fields.iteritems():
            if isinstance(v, list):
                tmp += v
            else:
                tmp.append(v)
        for k,v in self.ldap_only_fields.iteritems():
            if isinstance(v, list):
                tmp += v
            else:
                tmp.append(v)
        tmp.extend([k.ldap_field for k in self.get_ldap_m2m_relations() if k.is_local])
        return tmp

    def lval(self, instance=None, extra_attrs=[]): # value in LDAP
        dn = self.get_dn()
        instance = instance or self
        attrs = list(set(instance.ldap_attrs()+extra_attrs))
        return self.ldap.fetch(dn, filters=instance.ldap_filter, attrs=attrs, scope=ldap.SCOPE_BASE)

    @transaction.atomic
    def save(self, *args, **kwargs):
        self.full_clean() # .clean() adds information
        def _custom_changes_for_save(instance, kwargs):
            custom_changes = kwargs.pop('changes', None)
            if custom_changes:
                for k,v in custom_changes.iteritems():
                    setattr(instance, k, v['new'])
        _custom_changes_for_save(self, kwargs)
        self.changes_copy = self.get_changes()#store changes before post_save() cleans state
        super(LDAPModel, self).save(*args, **kwargs)

class LDAPGroupModel(LDAPModel):
    resources = generic.GenericRelation('fum.Resource')
    email = generic.GenericRelation('fum.EMails')

    def get_email(self):
        return get_generic_email(self.email)

    def get_email_editable(self):
        email = get_generic_email(self.email)
        return email.address if email else ''

    class Meta:
        abstract = True

class BaseGroup(LDAPGroupModel):
    """
    Current ldap_range is documented in models, with minimum enforced by DB sequence. No Boundary checks.
    """
    name = models.CharField(max_length=500, unique=True)
    description = models.CharField(max_length=5000, default="", blank=True)
    created = models.DateTimeField(null=True, blank=True, default=now)
    editor_group = models.ForeignKey('Groups', null=True, blank=True)
    users = UsersManyField('fum.Users', null=True, blank=True, related_name="%(app_label)s_%(class)s")
    
    ldap_id_field="cn"
    ldap_fields = {
                'description':'description',}
    ldap_only_fields = {
                'get_ldap_cn': 'cn',
            }
    # remove sambaGroupMapping only after sambaGroupType,sambaSID removed in LDAP for every entry
    ldap_object_classes = ['top', 'posixGroup', 'groupOfUniqueNames', 'mailRecipient', 'google', 'sambaGroupMapping']
    ldap_base_dn = settings.GROUP_DN
    ldap_id_number_field='gidNumber'

    restricted_fields = ['name', 'editor_group']

    def create_static_fields(self,ldap_id_number):
        static_attrs = {}
        if 'sambaGroupMapping' in self.ldap_object_classes:
            static_attrs['sambaGroupType'] = '2' # http://pig.made-it.com/samba-accounts.html
            static_attrs['sambaSID'] = '%s-%s' % (settings.SAMBASID_BASE, ldap_id_number * 2 + 1001)
        return static_attrs

    def get_ldap_id_value(self):
        return self.name

    def get_ldap_cn(self):
        return self.get_ldap_id_value()

    def is_member(self, user):
        if type(user) == types.StringType:
            try:
                user = Users.objects.get(username=user)
            except Users.DoesNotExist:
                return false
        return user in self.users.all()

    def email_aliases(self):
        email = get_generic_email(self.email)
        aliases = []
        if email:
            for alias in email.aliases:
                aliases.append(alias.address)
        return aliases

    def search_data(self):
        return u'%s %s'%(self.name, self.description)

    def __unicode__(self):
        return u'%s'%self.name

    class Meta:
        abstract = True
        ordering = ['name']


class SSHKey(models.Model):
    LDAP_OBJCLS = 'ldappublickey'
    LDAP_ATTR = 'sshPublicKey'

    title = models.CharField(max_length=50)
    key = models.TextField()
    user = models.ForeignKey('Users')

    # below fields computed on save
    fingerprint = models.CharField(max_length=100, unique=True, db_index=True)
    bits = models.IntegerField()

    @property
    def name(self):
        """
        The FUM changes api requires a name property for URL generation.
        """
        return self.fingerprint

    def save(self, *args, **kwargs):
        self.key = self.key.strip() if self.key else self.key
        k = sshpubkeys.SSHKey(self.key)
        self.bits = k.bits
        self.fingerprint = k.hash()
        self.full_clean()
        super(SSHKey, self).save(*args, **kwargs)

    def min_bits(self):
        """
        The minimum number of bits considered secure for the type of this key.
        """
        k = sshpubkeys.SSHKey(self.key)
        return settings.SSH_KEY_MIN_BITS_FOR_TYPE.get(k.key_type,
                settings.SSH_KEY_MIN_BITS_DEFAULT)

class Users(LDAPGroupModel):
    """ Phone1, Phone2 are both mobile numbers """
    UNDEFINED = 'undefined'
    ACTIVEPERSON = 'activeperson'
    ACTIVEMACHINE = 'activemachine'
    SUSPENDED = 'suspended'
    DELETED = 'deleted'
    GOOGLE_STATUS_CHOICES = (
        (UNDEFINED, 'undefined'),
        (ACTIVEPERSON, 'activeperson'),
        (ACTIVEMACHINE, 'activemachine'),
        (SUSPENDED, 'suspended'),
        (DELETED, 'deleted'),
    )
    SAMBA_PWD_EXPIRY_TIMESTAMP = '9876543210'

    USER_ACTIVE = 'active'
    USER_DISABLED = 'disabled'
    USER_DELETED = 'deleted'

    PLANMILL_DISABLED = 0
    PLANMILL_ACTIVE = 1
    PLANMILL_INACTIVE = 2
    ACTIVE_IN_PLANMILL_CHOICES = (
        (PLANMILL_DISABLED, 'Disabled'),
        (PLANMILL_ACTIVE, 'Active'),
        (PLANMILL_INACTIVE, 'Inactive'))

    def status_choices_xeditable(self):
         return [{'value': Users.USER_ACTIVE, 'text': 'Active'},
                 {'value': Users.USER_DISABLED, 'text': 'Disabled'},
                 {'value': Users.USER_DELETED, 'text': 'Deleted'},]

    def google_status_choices_xeditable(self):
         return [{'value':k, 'text':v} for k,v in Users.GOOGLE_STATUS_CHOICES]

    def planmill_status_choices_xeditable(self):
         return [{'value':json.dumps(k), 'text':v} for k,v in Users.ACTIVE_IN_PLANMILL_CHOICES]

    def __init__(self, *args, **kwargs):
        super(Users, self).__init__(*args, **kwargs)

    def in_group(self, group, user=None):
        user = user or self
        return user.username in group.users.all().order_by().values_list('username', flat=True)

    def update_password_fields(self, password):
        self.google_password = "" + hashlib.sha1(password.encode("utf8")).hexdigest()
        self.samba_password = smbpasswd.nthash(password)
        self.shadow_max = calculate_password_valid_days()
        self.shadow_last_change = (now() - EPOCH).days

    def expire_password(self, days_left=0):
        self.shadow_max = days_left
        self.shadow_last_change = (now().replace(year=now().year-1) - EPOCH).days

    first_name = models.CharField(max_length=500, blank=True, null=True)
    last_name = models.CharField(max_length=500)
    username = models.CharField(max_length=24, unique=True)
    title = models.CharField(max_length=500, null=True, blank=True)
    phone1 = models.CharField(max_length=100, null=True, blank=True)
    phone2 = models.CharField(max_length=100, null=True, blank=True)
    skype = models.CharField(max_length=100, null=True, blank=True)
    github = models.CharField(max_length=100, null=False, blank=True)
    physical_office = models.CharField(max_length=100, null=True, blank=True)
    google_status = models.CharField(max_length=255, choices=GOOGLE_STATUS_CHOICES, default=UNDEFINED)
    picture_uploaded_date = models.DateTimeField(null=True, blank=True, editable=False)
    suspended_date = models.DateTimeField(null=True, blank=True)
    publickey = models.TextField(null=True, blank=True)
    shadow_last_change = models.IntegerField(default=shadow_initial,null=True, blank=True,editable=False) # last time password was changed, in days since EPOCH
    shadow_max = models.IntegerField(default=calculate_password_valid_days,null=True, blank=True,editable=False) # how many days the password is valid
    portrait_thumb_name = models.CharField(max_length=500, null=True, blank=True)
    portrait_badge_name = models.CharField(max_length=500, null=True, blank=True)
    portrait_full_name = models.CharField(max_length=500, null=True, blank=True)
    home_directory = models.CharField(max_length=300, null=True, blank=True)
    created = models.DateTimeField(null=True, blank=True, default=now)
    hr_number = models.CharField(max_length=255, null=True, blank=True)
    active_in_planmill = models.IntegerField(default=PLANMILL_DISABLED, choices=ACTIVE_IN_PLANMILL_CHOICES)
    # FK
    supervisor = models.ForeignKey('self', null=True, blank=True)

    def get_status(self):
        groups = Groups.objects.filter(name__in=[settings.DELETED_GROUP, settings.DISABLED_GROUP])
        groups_users = {}
        for group in groups:
            groups_users.setdefault(group.name, [])
            for users in group.users.all().values_list('username', flat=True):
                groups_users[group.name].append(users)
        if not any(self.username in u for g,u in groups_users.iteritems()):
            return self.USER_ACTIVE
        if self.username in groups_users.get(settings.DELETED_GROUP, []):
            return self.USER_DELETED
        if self.username in groups_users.get(settings.DISABLED_GROUP, []):
            return self.USER_DISABLED
        raise

    def set_active(self):
        for group in [settings.DISABLED_GROUP, settings.DELETED_GROUP]:
            g,_ = Groups.objects.get_or_create(name=group)
            g.users.remove(self)

    def set_disabled(self):
        g,_ = Groups.objects.get_or_create(name=settings.DELETED_GROUP)
        g.users.remove(self)
        g,_ = Groups.objects.get_or_create(name=settings.DISABLED_GROUP)
        g.users.add(self)

        self.set_ldap_password(random_ldap_password())
        self.expire_password()
        self.save()

    def set_deleted(self):
        for g in self.fum_groups.all():
            g.users.remove(self)

        for g in self.fum_projects.all():
            g.users.remove(self)

        for g in self.fum_servers.all():
            g.sudoers.remove(self)
            g.users.remove(self)

        g,_ = Groups.objects.get_or_create(name=settings.DELETED_GROUP)
        g.users.add(self)

        self.set_ldap_password(random_ldap_password())
        self.google_status = self.DELETED
        self.expire_password()
        self.save()

    def audit_by_url(self):
        return reverse("audit") + "?uid=%s" % self.pk

    def get_absolute_name(self):
        return u'%s %s (%s)'%(self.first_name, self.last_name, self.username)

    @staticmethod
    def get_by_name():
        return 'username'
    
    @property
    def name(self):
        return self.username

    @property
    def password_expires_date(self):
        return EPOCH + relativedelta(days=self.shadow_last_change + self.shadow_max)

    @property
    def password_changed_date(self):
        return EPOCH + relativedelta(days=self.shadow_last_change)

    @property
    def portrait_full_file(self):
        return "%s%s" % (settings.PORTRAIT_FULL_FOLDER, self.portrait_full_name)

    @property
    def portrait_full_url(self):
        if not self.portrait_full_name:
            if self.portrait_thumb_name:#LDAP image migration only created thumbs
                return self.portrait_thumb_url
            return self.default_thumb_url()
        return "{0}{1}{2}".format(settings.API_URL, settings.PORTRAIT_FULL_URL, self.portrait_full_name)

    @property
    def portrait_thumb_file(self):
        return "%s%s" % (settings.PORTRAIT_THUMB_FOLDER, self.portrait_thumb_name)

    @property
    def portrait_thumb_url(self):
        if not self.portrait_thumb_name:
            return self.default_thumb_url()
        return "{0}{1}{2}".format(settings.API_URL, settings.PORTRAIT_THUMB_URL, self.portrait_thumb_name)

    @property
    def portrait_badge_file(self):
        return os.path.join(settings.PORTRAIT_BADGE_FOLDER,
                self.portrait_badge_name)

    @property
    def portrait_badge_url(self):
        if not self.portrait_badge_name:
            return self.default_thumb_url()
        return '{0}{1}{2}'.format(settings.API_URL,
                settings.PORTRAIT_BADGE_URL, self.portrait_badge_name)

    def default_thumb_url(self):
        return '{0}/static/img/default_portrait.jpeg'.format(settings.API_URL)

    def email_aliases(self):
        email = get_generic_email(self.email)
        aliases = []
        if email:
            for alias in email.aliases:
                aliases.append(alias.address)
        return aliases
    
    def set_ldap_password(self, password):
        self.password = password
        self.update_password_fields(password)
        self.save()
    
    ldap_id_field="uid"
    ldap_fields = {
                'username': ['uid','ntUserDomainId'],
                'first_name':'givenName',
                'last_name':'sn',
                'title': 'title',
                'phone1': 'telephoneNumber',
                'phone2': 'mobile',
                'google_status': 'googleStatus',
                'shadow_last_change': 'shadowLastChange',
                'shadow_max': 'shadowMax',
                'home_directory': 'homeDirectory',
                'physical_office': 'physicalDeliveryOfficeName',
                }
    ldap_only_fields = {
                'get_ldap_cn':  'cn',
                'password': 'userPassword',
                'google_password': 'googlePassword',
                'samba_password': 'sambaNTPassword',
                'samba_pwd_last_set': 'sambaPwdLastSet',
                'jpeg_portrait': 'jpegPhoto',
                'sshkey': SSHKey.LDAP_ATTR,
            }
    restricted_fields = ['username','phone1','phone2','google_status','suspended_date','password','active_in_planmill','hr_number',]
    # remove kerberos entries only after all People in LDAP purged of krb* data
    ldap_object_classes = ['inetOrgPerson', 'ntUser', 'account', 'hostObject', 'posixAccount', 'shadowAccount', 'sambaSamAccount', 'organizationalPerson', 'top', 'person', 'google','krbprincipalAux','krbTicketPolicyAux', SSHKey.LDAP_OBJCLS]
    ldap_base_dn=settings.USER_DN
    ldap_id_number_field='uidNumber'
    ldap_range=[10000,14999]

    def create_static_fields(self,ldap_id_number):
        static_attrs = {}
        if 'sambaSamAccount' in self.ldap_object_classes:
            static_attrs['sambaSID'] = '%s-%s' % (settings.SAMBASID_BASE, ldap_id_number * 2 + 1000)
            static_attrs['sambaAcctFlags'] = '[U          ]'
            static_attrs['sambaPwdLastSet'] = self.SAMBA_PWD_EXPIRY_TIMESTAMP
        if 'ntUser' in self.ldap_object_classes:
            static_attrs['ntUserCreateNewAccount'] = 'true'
            static_attrs['ntUserDeleteAccount'] = 'true'
            static_attrs['ntUserAcctExpires'] = '9223372036854775807' # 2^63 - 1
        static_attrs['loginShell'] = '/bin/bash'
        static_attrs['gidNumber'] = '2000'
        return static_attrs

    def get_ldap_id_value(self):
        return self.username

    def get_ldap_cn(self):
        return (u'%s %s'%(self.first_name or '', self.last_name or '')).strip()

    def search_data(self):
        return u'%s %s %s %s %s %s %s'%(self.username,
                self.first_name, self.last_name, self.title,
                self.phone1, self.phone2, self.github)

    def is_in_teamit(self):
        try:
            return self.username in Groups.objects.get(name=settings.IT_TEAM).users.all().values_list('username', flat=True)
        except Groups.DoesNotExist:
            return False

    def get_absolute_url(self):
        return reverse('users_detail', kwargs={'slug':self.username})

    # Removes spaces and dashes, substitutes 00 with +
    def clean_phone_number(self, phone_number):
        ret = phone_number.replace(' ','').replace('-','')
        if ret[:2] == '00':
            ret = '+' + ret[2:]
        return ret

    # turns 'https://github.com/TheUser/' into 'TheUser'
    def clean_github_username(self, value):
        pref, suf = 'https://github.com/', '/'
        if value.startswith(pref):
            value = value[len(pref):]
        if value.endswith(suf):
            value = value[:-len(suf)]
        return value

    def clean(self):
        # clean fields
        clean_for_ldap_on_creation = ['username']
        if not self.pk:
            for field in clean_for_ldap_on_creation:
                if getattr(self, field) is not None:
                    setattr(self, field, getattr(self, field).strip())
        clean_for_ldap = ['first_name','last_name']
        for field in clean_for_ldap:
            if getattr(self, field) is not None:
                setattr(self, field, getattr(self, field).strip())

        super(Users, self).clean()
        #
        # Field validations
        #
        if self.phone1 and len(self.phone1)>0 and not re.match(r'^(\+|00)[\d ]+$', str(self.phone1)):
            raise ValidationError('Invalid phonenumber. (Phone 1)')

        if self.phone2 and len(self.phone2)>0 and not re.match(r'^(\+|00)[\d ]+$', str(self.phone2)):
            raise ValidationError('Invalid phonenumber. (Phone 2)')

        if not re.match(r'^[\d\w\._\-,]*$', str(self.skype)):
            raise ValidationError('Invalid Skype username.')

        # Unify phone number formats
        if self.phone1:
            self.phone1 = self.clean_phone_number(self.phone1)
        if self.phone2:
            self.phone2 = self.clean_phone_number(self.phone2)
        self.github = self.clean_github_username(self.github)

        # Fill homedir if empty
        if not self.home_directory:
            self.home_directory = ('/home/%s/%s' % (self.username[0],self.username)).encode('ascii')

        # (django-history) Once in PlanMill, always in PlanMill
        if hasattr(self, 'get_changes'):
            changes = self.get_changes()
            if 'active_in_planmill' in changes and \
                changes['active_in_planmill']['old'] <> Users.PLANMILL_DISABLED \
                        and changes['active_in_planmill']['new'] == Users.PLANMILL_DISABLED:
                    raise ValidationError('Can not disable a once active PlanMill user')

    def is_sudo_user(self, request):
        actor = ActorPermission(request=request,
                instance=self)
        return actor.is_sudo_user()

    class Meta:
        ordering = ['first_name', 'last_name']

        
class Groups(BaseGroup):
    ldap_range = [15000, 19999]
    def get_absolute_url(self):
        return reverse('groups_detail', kwargs={'slug': self.name})

class Servers(BaseGroup):
    sudoers = SudoersManyField(Users, null=True, blank=True)

    ldap_object_classes = copy.deepcopy(BaseGroup.ldap_object_classes)
    ldap_object_classes.append('labeledURIObject')
    ldap_range = [20000, 24999]
    ldap_base_dn = settings.SERVER_DN
    ldap_fields = copy.deepcopy(BaseGroup.ldap_fields)

    def get_absolute_url(self):
        return reverse('servers_detail', kwargs={'slug':self.name})

    def get_ldap_sudoers_dn(self):
        return 'cn={0},{1}'.format(self.get_ldap_id_value(), settings.SUDO_DN)

    def create_static_fields(self, ldap_id_number):
        static_attrs = super(Servers, self).create_static_fields(ldap_id_number)
        return static_attrs

    def create_ldap_relations(self):
        # check for ManyFields, and get any record from there
        sudoers_record = [('objectClass', ['top','sudoRole']),
                          ('cn', [self.get_ldap_id_value().encode('ascii')]),
                          ('description', [('Permissions to use sudo on %s'%self.get_ldap_id_value()).encode('ascii')]),
                          ('sudoCommand', ['ALL']),
                          ('sudoHost', [('%s.futurice.com'%self.get_ldap_id_value()).encode('ascii')]),
                          ]
        self.ldap.create_raw(self.get_ldap_sudoers_dn(), sudoers_record)

PROJECT_NAME_REGEX = '^P([A-Z0-9][a-z0-9_-]+)([A-Z][A-Za-z0-9_-]+)$'
class Projects(BaseGroup):
    ldap_object_classes = copy.deepcopy(BaseGroup.ldap_object_classes)
    ldap_object_classes.append('labeledURIObject')

    ldap_base_dn = settings.PROJECT_DN
    ldap_range = [25000, 34999]

    def clean(self):
        if settings.ENFORCE_PROJECT_NAMING:
            if not self.created or self.created.replace(tzinfo=None) > settings.FUM_LAUNCH_DAY.replace(tzinfo=None): # LDAP has old names that fail on strict checks
                if not re.findall(PROJECT_NAME_REGEX, self.name):
                    raise ValidationError("Name is not valid. Format is: PCompanyProject")
        super(Projects, self).clean()

    def get_absolute_url(self):
        return reverse('projects_detail', kwargs={'slug':self.name})

class EMails(Mother):
    """ REMINDER: NOT AN LDAP MODEL """
    address = models.EmailField(max_length=254, blank=True, unique=True)

    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField(null=True)
    content_object = generic.GenericForeignKey('content_type', 'object_id')

    restricted_fields = ['address']
    ldap_field = 'mail'

    @property
    def name(self):
        return self.address

    @staticmethod
    def get_by_name():
        return 'address'

    @property
    def aliases(self):
        return EMailAliases.objects.filter(parent=self)

    def isEmailAddressValid(self, email):
        try:
            forms.EmailField().clean(email)
        except ValidationError:
            return False
        return True

    def clean(self):
        super(EMails, self).clean()
        if not self.isEmailAddressValid(self.address):
            if not self.address: # allow empty; TODO: have it remove EMail
                pass
            else:
                raise ValidationError("Email is not valid")
    
    @transaction.atomic
    def save(self, *args, **kwargs):
        self.address = self.address.strip()
        # DANGER: For GenericRelation as OneToOne-emulation to work (and EMailAliases to stay intact)
        # - UNIQUEness ValidationError is waived
        # - UPDATE first, on failure INSERT
        try:
            self.full_clean()
        except ValidationError, e:
            if 'not valid' in unicode(e):
                raise
            elif 'Enter a valid' in unicode(e):
                raise
            elif 'already exists' in unicode(e):
                pass
            else:
                raise
        try:
            existing_email = EMails.objects.filter(object_id=self.object_id, content_type=self.content_type)
            res = existing_email.update(address=self.address)
            if res==0:
                raise Exception
            existing_email = existing_email[0]
        except IntegrityError, e:
            raise ValidationError("Email is taken")
        except Exception, e:
            existing_email = None
            super(EMails, self).save(*args, **kwargs)
        email = existing_email or self
        try:
            # After super.save() no failures allowed.
            self.content_object.ldap.replace_relation(parent=self.content_object, child=u'%s'%self.address, field=self)
            # create identical alias for username@futurice.com
            if settings.EMAIL_DOMAIN in self.address and isinstance(self.content_object, Users):
                em, _ = EMailAliases.objects.get_or_create(parent=email, address='{0}{1}'.format(self.content_object.username, settings.EMAIL_DOMAIN))
        except Exception, e:
            print "EMails",e

    class Meta:
        unique_together = ('content_type', 'object_id') # OneToOne emulation for GenericForeignKey

class EMailAliases(Mother):
    """ REMINDER: NOT AN LDAP MODEL

    Aliases are forwarding addresses that should be unique.
    For forwarding a Group email, add a User to it, not an email address.
    """
    address = models.EmailField(max_length=254, unique=True)
    parent = models.ForeignKey(EMails)

    restricted_fields = ['address']
    ldap_field = 'proxyaddress'

    @staticmethod
    def get_by_name():
        return 'address'

    @property
    def name(self):
        return self.address

    def clean(self):
        if EMailAliases.objects.filter(address=self.address):
            raise ValidationError('Alias already in use')

        existing_email = EMails.objects.filter(address=self.address).first()
        if existing_email and existing_email.address.strip() == self.address.strip():
            raise ValidationError('Alias conflicts with an existing Email address')

        super(EMailAliases, self).clean()

    @transaction.atomic
    def save(self, *args, **kwargs):
        # all model fields always required, manual clean here should be fine: https://code.djangoproject.com/ticket/13100
        self.full_clean()
        ret = super(EMailAliases, self).save(*args, **kwargs)
        try:
            # After super.save() no failures allowed.
            self.parent.content_object.ldap.save_relation(parent=self.parent.content_object, child=u'%s'%self.address, field=self)
        except Exception, e:
            pass
        return ret

class Resource(Mother):
    name = models.CharField(max_length=500)
    url = models.URLField(max_length=500)
    archived = models.BooleanField(default=False)

    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey('content_type', 'object_id')

    def clean_url(self):
        # append http://, if no schema given
        if not re.match(r'^.*://.*', unicode(self.url)):
            self.url = u'http://%s'%self.url

    def save(self, *args, **kwargs):
        self.clean_url()
        self.full_clean()
        super(Resource, self).save(*args, **kwargs)

    def get_absolute_name(self):
        return u'%s (resource)'%self.name

    def get_absolute_url(self):
        return u'/'

# Monkey see, monkey do | add method to django's auth user
def get_fum_user(self):
    try:
        fum_user = Users.objects.get(username=self.username)
    except Users.DoesNotExist:
        fum_user = None
    return fum_user
User.add_to_class("get_fum_user", get_fum_user)

#
#
# LDAP relations -> see .m2m.py
#
#


#
#
# SIGNALS
#
#
from fum.common.signals import *

# CIRCULAR IMPORTS AT BOTTOM
from fum.permission import ActorPermission
