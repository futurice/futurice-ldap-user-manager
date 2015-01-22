from django.conf import settings
from django.dispatch import receiver
from django.db.models.signals import pre_delete, post_delete, post_init, post_save, m2m_changed, pre_save
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError

from fum.api.changes import changes_update_m2m
from fum.common.middleware import get_current_request
from fum.decorators import receiver_subclasses
from fum.models import LDAPModel, Groups, Servers, Projects, Users, EMailAliases, EMails, Resource

from pprint import pprint as pp
import ldap
import copy, logging

log = logging.getLogger(__name__)

#
# post_save
#

@receiver(post_delete, sender=Projects)
def projects_email(sender, *args, **kwargs):
    from fum.projects.util import name_to_email
    instance = kwargs['instance']
    if kwargs.get('created', False):
        e,_ = EMails.objects.get_or_create(
                object_id=instance.pk,
                content_type=ContentType.objects.get_for_model(instance),
                address=name_to_email(instance.name))

#
# post_delete
# NOTE: for relations, parent object might be already deleted, causing NO_SUCH_OBJECT errors
#

@receiver(post_delete, sender=EMails)
def email_delete(sender, *args, **kwargs):
    instance = kwargs['instance']
    if instance.content_object:
        try:
            instance.content_object.ldap.delete_relation(parent=instance.content_object, child=u'%s'%instance.address, field=instance)
        except ldap.NO_SUCH_OBJECT, e:
            pass

@receiver(post_delete, sender=EMailAliases)
def email_alias_delete(sender, *args, **kwargs):
    instance = kwargs['instance']
    try:
        parent = instance.parent.content_object
    except (ObjectDoesNotExist), e:
        # if parent is gone, aliases are also gone
        log.debug(e)
        return
    if not parent:
        return
    try:
        parent.ldap.delete_relation(parent=parent, child=u'%s'%instance.address, field=instance)
    except ldap.NO_SUCH_OBJECT, e:
        pass

#
# pre_delete
#

@receiver_subclasses(pre_delete, LDAPModel, 'ldap_post_delete')
def ldap_delete(sender, *args, **kwargs):
    # Delete a model in LDAP after it has been deleted in Django.
    instance = kwargs['instance']
    if instance.ldap_fields is not None:
        instance.ldap.delete()
    #TODO: If this fails the LDAP is in a different state than FUM, should notify.

def clean_sudoers(sender, *args, **kwargs):
    instance = kwargs['instance']
    try:
        instance.ldap.delete(dn=instance.get_ldap_sudoers_dn())
    except Exception, e:
        pass # if LDAP was out of sync, it is not anymore (given LDAP was up...); all is OK.
pre_delete.connect(clean_sudoers, sender=Servers)

#
#
# M2M
#
#

def can_add_relation(parent, child, field):
    """
    Groups:
    - being part of editor_group
    - anything but settings.PROTECTED_GROUPS
    """
    request = get_current_request()
    return parent.can_edit(request, instance=parent, child=child, field=field)

def can_remove_relation(parent, child, field):
    request = get_current_request()
    return parent.can_m2m_remove(request, instance=parent, child=child, field=field)

def ldap_m2m(sender, **kwargs):
    """
    Handles saving of ManyToMany relation into correct LDAP table, after it has been saved to database.
    A model's save() never gets called on ManyToManyField changes, m2m_changed-signal is sent.

    sender = dynamically generated model in m2m-table
    instance = parent; eg. server in server.add(user)
    related_instance = instance being added, eg. user
    """
    action = kwargs['action']
    instance = kwargs['instance']
    if action in ['pre_add','pre_remove','post_add','post_remove']:
        pk_set = list(kwargs['pk_set'])
        relation_name = sender._meta.db_table.split('_')[-1]
        if pk_set: # TODO: iterate pk_set
            relations = {k.name:k for k in instance.get_ldap_m2m_relations()}
            related_instance = relations[relation_name].related.parent_model.objects.get(pk=pk_set[0])
            field = relations[relation_name]

            if action == 'post_add':
                try:
                    instance.ldap.save_relation(parent=instance, child=related_instance, field=field)
                except ldap.TYPE_OR_VALUE_EXISTS, e:
                    log.debug("{}: {}".format(action, field.get_dn(instance, related_instance), e))
            elif action == 'post_remove':
                try:
                    instance.ldap.delete_relation(parent=instance, child=related_instance, field=field)
                except ldap.NO_SUCH_ATTRIBUTE, e:
                    log.debug("{}: {}".format(action, field.get_dn(instance, related_instance), e))
            elif action == 'pre_add':
                if not can_add_relation(instance, related_instance, field):
                    raise ValidationError("M2M action not authorized")
            elif action == 'pre_remove':
                if not can_remove_relation(instance, related_instance, field):
                    raise ValidationError("M2M action not authorized")
            else: raise Exception("Unsupported m2m action")

            try:
                # ALL CODE AFTER LDAP CHANGES WRAPPED IN A TRY/EXCEPT: FAILURE IS NOT AN OPTION.
                changes_m2m(sender, instance, action, related_instance)
            except Exception, e:
                log.debug(e)

def changes_m2m(sender, instance, action, related_instance):
    # CHANGES DATA FOR WEBSOCKET: full list of old and current entries
    relation_name = sender._meta.db_table.split('_')[-1]
    values = getattr(instance, relation_name).all()

    new_vals = [k.name for k in values]
    old_vals = copy.deepcopy(new_vals)
    if action == 'post_add':
        old_vals = copy.deepcopy(new_vals)
        old_vals.remove(related_instance.name)
    elif action == 'post_remove':
        old_vals.append(related_instance.name)
    changes_update_m2m(instance, relation_name, old_vals, new_vals, action, related_instance)

for k in [Groups.users.through, Servers.users.through, Projects.users.through, Servers.sudoers.through]:
    m2m_changed.connect(ldap_m2m, sender=k)


def remove_sudo(sender, *args, **kwargs):
    action = kwargs['action']
    server = kwargs['instance']
    if action == 'post_remove':
        pk_set = list(kwargs['pk_set'])
        for user in Users.objects.filter(id__in=pk_set):
            server.sudoers.remove(user)

# removing user from Server causes removal from sudoers also
m2m_changed.connect(remove_sudo, sender=Servers.users.through)

def injection():
    """ This do-nothing function is here, called in ldap_save(), until I figure out how to mock Django signals in tests """
    pass

def ldap_save(sender, instance, created, **kwargs):
    injection()
    changes = copy.deepcopy(instance.changes_copy)
    changes.update(instance.get_changes('ldap'))

    if created:
        changes.update(instance.get_changes())# primary key -information
        new_attrs = {}
        new_attrs['objectClass'] = instance.ldap_object_classes
        new_attrs[instance.ldap_id_number_field] = str(instance.pk)
        new_attrs.update(instance.create_static_fields(ldap_id_number=instance.pk))

        try:
            # .create_raw() for Servers SUDOers is problematic.
            # - related records should never cause failure
            instance.create_ldap_relations()
        except ldap.ALREADY_EXISTS, e:
            print e

        try:
            instance.ldap.create(dn=instance.get_dn(), values=changes, extra=new_attrs)
        except ldap.ALREADY_EXISTS, e:
            instance.ldap.save(force_update=True)
    else:
        instance.ldap.save(values=changes)

post_save.connect(ldap_save, sender=Users)
post_save.connect(ldap_save, sender=Groups)
post_save.connect(ldap_save, sender=Servers)
post_save.connect(ldap_save, sender=Projects)

#
# WEBSOCKET ENDPOINT
#

from fum.api.changes import changes_save
post_save.connect(changes_save, sender=Groups)
post_save.connect(changes_save, sender=Servers)
post_save.connect(changes_save, sender=Projects)
post_save.connect(changes_save, sender=Users)
post_save.connect(changes_save, sender=EMails)
post_save.connect(changes_save, sender=EMailAliases)
post_save.connect(changes_save, sender=Resource)

post_save.connect(projects_email, sender=Projects)
