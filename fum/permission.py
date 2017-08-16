from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User

from rest_framework.authtoken.models import Token

from ldap_helpers import AttrDict
from pprint import pprint as pp

class ActorPermission(object):
    """
    PERMISSIONS CHECKS:
    0. everyone can edit everything, except user data and restricted fields
    1. user can edit their own profile
    2. user can edit a group
        if they belong to the group's editor_group
        if editor_group is None
    3. IT team can edit anything in SUDO mode (only available for IT)

    4. Token access is granted read+write, except for restricted groups

    editable (everyone)
    restricted (sudo)
    password (owner, sudo)
    """
    def __init__(self, instance, request, child=None, field=None):
        self.instance = instance
        self.request = request
        self.child = child
        self.field = field
        self.P = AttrDict(failures=[], whitelist=[])
        self.cache = {}
        self.instance_to_check = self.get_parent_model() or self.instance

    def is_sudo_user(self):
        return bool(self.request.session.get('sudo_timeout', False))
    
    def has_pk(self):
        return hasattr(self.instance, 'pk') and self.instance.pk is not None

    def is_token_user(self):
        """ A token User is an AnonymouserUser """
        if not self.cache.get('IS_TOKEN_USER'):
            token = self.request.META.get('HTTP_AUTHORIZATION', None)
            if not token:
                return False
            token = token.replace('Token', '').strip()
            try:
                result = Token.objects.filter(key=token).values('key')[0]
            except:
                result = False
            self.cache['IS_TOKEN_USER'] = result
        return self.cache.get('IS_TOKEN_USER')

    def token_user_whitelist(self):
        has_token = self.is_token_user()
        if has_token:
            if not self.is_protected_group():
                self.P.whitelist.append('Token has unlimited read+write')

    def get_parent_model(self):
        instance_to_check = None
        if isinstance(self.instance, EMails):
            instance_to_check = self.instance.content_object
        if isinstance(self.instance, Resource):
            instance_to_check = self.instance.content_object
        return instance_to_check

    def editor_group_restriction(self):
        if isinstance(self.instance_to_check, BaseGroup):
            if self.instance_to_check.editor_group:
                if self.request.user.username in self.instance_to_check.editor_group.users.all().order_by().values_list('username', flat=True):
                    pass
                else:
                    self.P.failures.append('Groups.editor_group is set for ({0}) and user is not part of group'.format(self.instance_to_check))

    def has_permission(self):
        if self.P.whitelist:
            return True
        return (not self.P.failures)

    def is_protected_group(self):
        if isinstance(self.instance_to_check, Groups):
            if self.instance_to_check.name in settings.PROTECTED_GROUPS:
                return True
        return False

    def protected_groups(self):
        if self.is_protected_group():
            if not self.is_in_it():
                self.P.failures.append("PROTECTED_GROUPS ({0}) can only be modified by IT".format(self.instance_to_check.name))

    def restricted_fields(self):
        changes = self.instance.get_changes()
        if not self.instance._state.adding:
            for k in self.instance.restricted_fields:
                if k in changes.keys():
                    if k in ['password'] \
                            and (type(self.instance) in [User, Users]) \
                            and self.instance.username == self.request.user.username:
                        continue
                    if self.is_token_user():
                        continue
                    if self.instance.username == self.request.user.username:
                        continue
                    if self.is_in_it():
                        continue
                    self.P.failures.append('Accessing restricted field ({0}), and user ({1}) is not the owner ({2})'.format(k,
                        self.request.user.username,
                        self.instance.username))
    def can_create(self):
        return True

    def owner_can_edit_profile(self):
        if not self.has_pk() and self.can_create():
            return
        if isinstance(self.instance_to_check, Users):
            if self.instance_to_check.username == self.request.user.username:
                self.P.whitelist.append('Owner editing itself')
            else:
                self.P.failures.append('Only owner ({0}) can edit User information. Denied: {1}.'.format(
                    self.instance_to_check.username,
                    self.request.user.username))

    def owner_can_m2m_profile(self):
        if isinstance(self.instance_to_check, Users):
            if self.instance_to_check.username == self.request.user.username:
                self.P.whitelist.append('Owner m2m itself')

    def is_in_it(self):
        if not self.cache.get('IS_IN_IT'):
            is_in_it_team = False
            try:
                user = Users.objects.get(username=self.request.user.username)
                is_in_it_team = user.is_in_teamit()
            except Exception, e:
                if settings.DEBUG:
                    print e
            self.cache['IS_IN_IT'] = is_in_it_team
        return self.cache.get('IS_IN_IT')

    def can_base_check(self):
        is_token_user = self.is_token_user()
        if isinstance(self.request.user, AnonymousUser) and not is_token_user:
            self.P.failures.append('Anonymous User access denied')
        is_sudo_user = self.is_sudo_user()
        if is_sudo_user:
            self.P.whitelist.append('SUDO enabled')
        self.is_in_it()
        if hasattr(self.instance, 'skip_ldap') and self.instance.skip_ldap:
            self.P.whitelist.append('email uniqueness delete allowed')
        self.editor_group_restriction()

    def has_user_permission_to_delete(self):
        perm_name = 'fum.delete_%s'%self.instance.__class__.__name__.lower()
        if self.request.user.has_perm(perm_name):
            self.P.whitelist.append('has_perm {0}'.format(perm_name))
        else:
            self.P.failures.append("No access to delete, missing permission: {0}".format(perm_name))

    def run_chain(self, checks):
        if self.request:
            for check_fn in checks:
                check_fn()
                if self.P.whitelist:
                    return
        else:
            self.P.whitelist.append('superuser via shell')

    def can_edit(self):
        self.run_chain([
            self.can_base_check,
            self.restricted_fields,
            self.owner_can_edit_profile,
            self.protected_groups,
            self.token_user_whitelist,
        ])

    def can_delete(self):
        self.run_chain([
            self.can_base_check,
            self.protected_groups,
            self.owner_can_m2m_profile,
            self.has_user_permission_to_delete,
        ])

    def can_m2m_remove(self):
        self.run_chain([
            self.can_base_check,
            self.protected_groups,
            self.owner_can_edit_profile,
        ])

# CIRCULAR IMPORTS AT BOTTOM
from models import Users, Groups, EMails, Resource, BaseGroup
