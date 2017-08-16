from django.conf import settings
from django.dispatch import receiver
from django.db.models.signals import pre_delete, post_delete, post_init, post_save, m2m_changed, pre_save
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError

from fum.api.changes import changes_update_m2m
from fum.common.middleware import get_current_request
from fum.decorators import receiver_subclasses
from fum.models import LDAPModel, Groups, Servers, Projects, Users, EMails, Resource, ldap_email, ldap_emailalias

import ldap
import copy, logging

log = logging.getLogger(__name__)

#
# post_save
#

def project_default_email(sender, *args, **kwargs):
    from fum.projects.util import name_to_email
    instance = kwargs['instance']
    if kwargs.get('created', False):
        kw = dict(object_id=instance.pk, content_type=ContentType.objects.get_for_model(instance))
        if not EMails.objects.filter(**kw).exists():
            e,_ = EMails.objects.get_or_create(address=name_to_email(instance.name), **kw)

#
# pre_save
#

def email_unique(sender, *args, **kwargs):
    # remove any existing parent
    instance = kwargs['instance']
    if instance.alias:
        return
    kw = dict(object_id=instance.content_object.pk,
              content_type=ContentType.objects.get_for_model(instance.content_object),
              alias=False)
    # when removing parent, its fine for aliases to remain as forwarding addresses
    emails = EMails.objects.filter(**kw)
    for email in emails:
        try:
            email.skip_ldap = True
            email.delete()
        except Exception as e:
            print(e)
            pass

@receiver(post_save, sender=EMails)
def save_email(sender, *args, **kwargs):
    instance = kwargs['instance']
    if instance.alias:
        # proxyaddress = save_relation (add)
        instance.content_object.ldap.save_relation(parent=instance.content_object, child=u'%s'%instance.address, field=ldap_emailalias(instance))
    else:
        # email = replace_relation (add/modify)
        instance.content_object.ldap.replace_relation(parent=instance.content_object, child=u'%s'%instance.address, field=ldap_email(instance))
        # create alias: username@futurice.com
        if settings.EMAIL_DOMAIN in instance.address and isinstance(instance.content_object, Users):
            username_email = dict(address='{0}{1}'.format(instance.content_object.username, settings.EMAIL_DOMAIN))
            if not EMails.objects.filter(**username_email).exists():
                try:
                    em = EMails(content_object=instance.content_object,
                                alias=True,
                                **username_email)
                    em.save()
                except Exception as e:
                    pass

#
# post_delete
# NOTE: for relations, parent object might be already deleted, causing NO_SUCH_OBJECT errors
#

@receiver(post_delete, sender=EMails)
def email_delete(sender, *args, **kwargs):
    instance = kwargs['instance']
    if instance.content_object:
        if hasattr(instance, 'skip_ldap'):
            return
        fn = ldap_email
        if instance.alias:
            fn = ldap_emailalias
        try:
            instance.content_object.ldap.delete_relation(parent=instance.content_object, child=u'%s'%instance.address, field=fn(instance))
        except (ldap.NO_SUCH_OBJECT, ldap.NO_SUCH_ATTRIBUTE) as e:
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
                except (ldap.NO_SUCH_ATTRIBUTE, ldap.NO_SUCH_OBJECT) as e:
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
    changes = dict(instance.changes_copy)
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
post_save.connect(changes_save, sender=Resource)

post_save.connect(project_default_email, sender=Projects)
pre_save.connect(email_unique, sender=EMails)
