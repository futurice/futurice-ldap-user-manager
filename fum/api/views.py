from django.conf import settings
from django.core.paginator import Paginator,PageNotAnInteger, EmptyPage
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.core.cache import cache
from django.db.models import Q

from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action, link
from rest_framework.pagination import PaginationSerializer
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework import serializers as drf_serializers

import sshpubkeys
from serializers import *

from fum.api.changes import changes_save, changes_delete
from fum.ldap_helpers import test_user_ldap
from fum.models import EMailAliases, Resource, Users, SSHKey
from fum.common.util import SMS, random_ldap_password
from fum.api.serializers import UsersSerializer

import ldap
from ldap import CONSTRAINT_VIOLATION
from datetime import datetime
from PIL import Image
import os, os.path
import pytz
import json
from pprint import pprint as pp

from rest_framework import renderers
class JPEGRenderer(renderers.BaseRenderer):
    media_type = 'image/jpeg'
    format = 'jpg'
    charset = None
    render_style = 'binary'

    def render(self, data, media_type=None, renderer_context=None):
        return data

def mod_resources(request, o):
    data = request.DATA
    if request.method != 'GET':
        if request.method in ['PATCH', 'POST']:
            if data.get('pk'): # PATCH
                resource = Resource.objects.get(pk=data.get('pk'))
                for k,v in data['value'].iteritems():
                    setattr(resource, k, v)
                
                resource.save()

            else: # POST
                resource = Resource(content_object=o, **data['value'])
                resource.save()
        if request.method == 'DELETE':
            if data.get('pk'):
                resource = Resource(content_object=o, pk=data.get('pk'))
                resource.delete()
    r = []
    for k in o.resources.all().values().order_by():
        r.append(dict(
            id=k['id'],
            name=k['name'],
            url=k['url'],
            archived=k['archived']))
    r = sorted(r, key=lambda k: k['id'])
    return Response(r, status=status.HTTP_200_OK)

def receive_input(request, relname=None):
    """ support for .post(string), post([string]) and .post({'items': []}) for relations """
    r = None
    if relname is not None:
        r = [relname]
    elif isinstance(request.DATA, list):
        r = request.DATA
    elif isinstance(request.DATA, basestring):
        r = [request.DATA]
    elif isinstance(request.DATA, dict):
        if hasattr(request.DATA, 'getlist'):
            r = request.DATA.getlist('items')
        else:
            r = request.DATA['items']
    return r

def mod_users(request, group_members, relname=None):
    if request.method != 'GET':
        try:
            usernames = receive_input(request, relname=relname)
        except KeyError:
            content = {'detail': 'Username not found in request.'}
            return Response(content, status=status.HTTP_400_BAD_REQUEST)
        
        users = []
        for username in usernames:
            if len(username)>0:
                try:
                    user = Users.objects.get(username=username)
                except:
                    content = {'detail': 'User not found'}
                    return Response(content, status=status.HTTP_404_NOT_FOUND)
                users.append(user);
        
        if request.method == 'POST':
            for user in users:
                try:
                    group_members.add(user)
                except ValidationError as e:
                    return Response(e.messages, status=403)

        elif request.method == 'DELETE':
            for user in users:
                try:
                    group_members.remove(user)
                except ValidationError as e:
                    return Response(e.messages, status=403)
    
    json_users = []
    for user in group_members.all().values().order_by():
        json_user={}
        json_user['username'] = user['username']
        json_user['first_name'] = user['first_name']
        json_user['last_name'] = user['last_name']
        json_user['google_status'] = user['google_status']
        json_users.append(json_user)
    json_users = sorted(json_users, key=lambda k: k['username'])

    return Response(json_users, status=status.HTTP_200_OK)

def mod_groups(request, user, usergroups, classname):
    if request.method != 'GET':
        try:
            groupnames = receive_input(request)
        except KeyError:
            content = {'detail': 'No groups found.'}
            return Response(content, status=status.HTTP_400_BAD_REQUEST)
        
        groups = []
        for groupname in groupnames:
            if len(groupname)>0:
                try:
                    group = classname.objects.get(name=groupname)
                    groups.append(group);
                except:
                    content = {'detail': '%s not found, nothing changed.'%groupname}
                    return Response(content, status=status.HTTP_404_NOT_FOUND)
        
        if request.method =='DELETE':
            for group in groups:    
                if group in usergroups.all():
                    group.users.remove(user)

        elif request.method == 'POST':
            for group in groups:
                if user not in group.users.all():
                    group.users.add(user)

    json_groups = []
    for group in usergroups.all().values().order_by():
        json_group = {}
        json_group['name'] = group['name']
        if classname == Servers:
            json_group['sudo'] = user.username in Servers.objects.get(pk=group['id']).sudoers.all().values_list('username', flat=True).order_by()
        json_groups.append(json_group)
    json_groups = sorted(json_groups, key=lambda k: k['name'])

    return Response(json_groups, status=status.HTTP_200_OK)

class ListMixin(object):
    def list(self, request):
        limit = request.QUERY_PARAMS.get(settings.REST_FRAMEWORK['PAGINATE_BY_PARAM'], None)
        try:
            limit = int(limit)
        except:
            limit = settings.REST_FRAMEWORK['PAGINATE_BY']

        if limit is None or limit > 0:
            paginator = Paginator(self.get_queryset(), limit)

            page = request.QUERY_PARAMS.get('page')
            try:
                users = paginator.page(page)
            except PageNotAnInteger:
                users = paginator.page(1)
            except EmptyPage:
                users = paginator.page(paginator.num_pages)

            serializer_context = {'request': request}
            serializer = self.paginated_serializer_class(users,context=serializer_context)
        else:
            serializer = self.list_serializer_class(self.get_queryset(), many=True)
        
        return Response(serializer.data)

class BaseViewSet(viewsets.ModelViewSet):
    lookup_value_regex = '[^/]+'

class LDAPViewSet(viewsets.ModelViewSet):
    lookup_value_regex = '[^/]+'# fix for restframework regression moving from 2.3->2.4

    def get_queryset(self):
        return self.model.objects.all()

    @action(methods=['post', 'delete', 'get'])
    def aliases(self, request, username=None, name=None):
        obj = self.get_object()
        email = obj.get_email()
        aliases = []

        if request.method != 'GET':
            try:
                items = receive_input(request)
            except KeyError, e:
                print e
                content = {'detail': 'No aliases found.'}
                return Response(content, status=status.HTTP_400_BAD_REQUEST)

            if request.method =='DELETE':
                for alias in items:
                    try:
                        a = EMailAliases.objects.get(address=alias, parent=email).delete()
                    except ValidationError as e:
                        return Response(e.messages, status=403)
                    except KeyError: 
                        pass # TODO: Error message or just return current aliases?

            elif request.method == 'POST':
                for alias in items:
                    try:
                        a = EMailAliases.objects.create(address=alias, parent=email)
                    except Exception, e:
                        return Response(e.messages, status=400)
                
        
        if email:
            for alias in email.aliases:
                aliases.append(alias.address)
        
        return Response(aliases, status=status.HTTP_200_OK)

    @action(methods=['post', 'delete', 'get', 'patch'])
    def resources(self, request, username=None, name=None):
        return mod_resources(request, self.get_object())

    def destroy(self, request, *args, **kwargs):
        try:
            return super(LDAPViewSet, self).destroy(request,args,kwargs)
        except ValidationError as e:
            return Response("Access denied", status=403)

class UsersViewSet(ListMixin, LDAPViewSet):
    model = Users
    serializer_class = UsersSerializer
    lookup_field = 'username'
    list_serializer_class = UsersListSerializer
    paginated_serializer_class = PaginatedUsersSerializer

    def get_queryset(self):
        email = self.request.QUERY_PARAMS.get('email', None)
        name = self.request.QUERY_PARAMS.get('name', None)
        username = self.request.QUERY_PARAMS.get('username', None)
        id = self.request.QUERY_PARAMS.get('id', None)
        if email is not None:
            # NOTE: vscfum needs changes if modifying this
            return self.model.objects.filter(email__address__icontains=email)
        elif name is not None:
            return self.model.objects.filter(Q(username__icontains=name) | Q(first_name__icontains=name) | Q(last_name__icontains=name))
        elif username is not None:
            return self.model.objects.filter(Q(username__icontains=username))
        elif id is not None:
            return self.model.objects.filter(id=id)
        else:
            return self.model.objects.all()

    @action(methods=['post', 'delete', 'get'])
    def groups(self, request, username=None, relname=None):
        user = self.get_object()
        groups = user.fum_groups
        return mod_groups(request, user, groups, Groups)

    @action(methods=['post', 'delete', 'get'])
    def servers(self, request, username=None, relname=None):
        user = self.get_object()
        servers = user.fum_servers
        return mod_groups(request, user, servers, Servers)
    
    @action(methods=['post', 'delete', 'get'])
    def projects(self, request, username=None, relname=None):
        user = self.get_object()
        projects = user.fum_projects
        return mod_groups(request, user, projects, Projects)        

    @action(methods=['post'])
    def password(self, request, username=None, relname=None):
        user = self.get_object()
        old_password = None
        try:
            password = request.DATA['password']
            old_password = request.DATA['old_password']
        except KeyError:
            pass
        # TODO: add smart error case catching

        if user.is_sudo_user(request) or (old_password and test_user_ldap(user.username, old_password)) or request.user.has_perm('fum.add_users'):
            try:
                user.set_ldap_password(password)
                return Response("Ok", status=200)
            except Exception, e:
                return Response("Fail: %s"%e, status=500)
        else:
            return Response("Old password fail", status=403)

    # TODO: Faster failing option: try to first write to ldap, only then save the image files to disk?
    @action(methods=['post'])
    def portrait(self, request, username=None):
        user = self.get_object()
        data = request.DATA['portrait']
        crop = tuple(max(0, int(request.DATA[k]))
                for k in ('left', 'top', 'right', 'bottom'))
        if crop == (0, 0, 0, 0):
            crop = (0, 0, 320, 480)
        image = data[data.find('base64,')+7:].decode('base64')

        now = datetime.now(pytz.utc)
        now_local = now.astimezone(pytz.timezone("Europe/Helsinki"))
        now_str = now_local.strftime('%Y%m%d%H%M%S')
        
        # let's save the full image...
        portrait_file_name = '%s%s.jpeg' % (user.username, now_str)
        portrait_file_path = os.path.join(settings.PORTRAIT_FULL_FOLDER,
                portrait_file_name)
        with open(portrait_file_path, 'wb') as portrait_file:
            portrait_file.write(image)

        # ...and then the (cropped) thumb
        thumb = Image.open(portrait_file_path)
        # crop the image and resize it to the official 320x480 format
        thumb = thumb.crop(crop).resize((320,480))

        # make sure we have a jpeg compatible image to save
        if thumb.mode != "RGB":
            thumb = thumb.convert("RGB")

        # save the thumbnail to a file
        thumb_file_name = '%s%s_%s_%s_%s_%s.jpeg' % (user.username, now_str, crop[0], crop[1], crop[2], crop[3])
        thumb_file_path = os.path.join(settings.PORTRAIT_THUMB_FOLDER,
                thumb_file_name)
        with open(thumb_file_path, 'wb') as thumb_file:
            thumb.save(thumb_file, 'JPEG', quality=100) # Full quality jpeg file

        # set the same file as a string for the user (for ldap sending)
        with open(thumb_file_path, 'rb') as thumb_file:
            user.jpeg_portrait = thumb_file.read()

        # save the badge photo
        badge = Image.open(portrait_file_path).crop(crop)
        badge_file_name = '{}{}_{}_{}_{}_{}.png'.format(user.username, now_str,
                *crop)
        badge_file_path = os.path.join(settings.PORTRAIT_BADGE_FOLDER,
                badge_file_name)
        with open(badge_file_path, 'wb') as badge_file:
            badge.save(badge_file, 'PNG')

        # update the timestamp and file names
        user.picture_uploaded_date = now
        user.portrait_thumb_name = thumb_file_name
        user.portrait_badge_name = badge_file_name
        user.portrait_full_name = portrait_file_name

        try: # try to save to local db and ldap
            user.save()
        except Exception, e: # save failed, remove the uploaded images and return error
            os.remove(thumb_file_path)
            os.remove(portrait_file_path)
            os.remove(badge_file_path)
            return Response("Error writing to LDAP", status=500)

        # alles gut, return the urls to the new images
        ret = {
            'thumb': '%s%s' % (settings.PORTRAIT_THUMB_URL, thumb_file_name),
            'full': '%s%s' % (settings.PORTRAIT_FULL_URL, portrait_file_name),
            'badge': '{}{}'.format(settings.PORTRAIT_BADGE_URL, badge_file_name),
            'day': now_local.strftime('%Y/%m/%d'),
            'time': now_local.strftime('%H:%M:%S'),
        }
        return Response(json.dumps(ret), status=200)

    @action(methods=['post'])
    def badgecrop(self, request, username=None):
        """
        Make a new "badge crop" out of the existing portrait image.
        """
        user = self.get_object()
        if (request.user.username != user.username and
                not user.is_sudo_user(request)):
            return Response('Forbidden', status=403)
        crop = tuple(max(0, int(request.DATA[k]))
                for k in ('left', 'top', 'right', 'bottom'))

        now = datetime.now(pytz.utc)
        now_local = now.astimezone(pytz.timezone("Europe/Helsinki"))
        now_str = now_local.strftime('%Y%m%d%H%M%S')

        badge = Image.open(user.portrait_full_file).crop(crop)
        badge_file_name = '{}{}_{}_{}_{}_{}.png'.format(user.username, now_str,
                *crop)
        badge_file_path = os.path.join(settings.PORTRAIT_BADGE_FOLDER,
                badge_file_name)
        with open(badge_file_path, 'wb') as badge_file:
            badge.save(badge_file, 'PNG')
        user.portrait_badge_name = badge_file_name

        try:
            user.save()
        except Exception, e:
            os.remove(badge_file_path)
            return Response("Error saving the user data", status=500)

        ret = {
            'badge': '{}{}'.format(settings.PORTRAIT_BADGE_URL,
                badge_file_name),
        }
        return Response(json.dumps(ret), status=status.HTTP_200_OK)

    @action(methods=['get','post','patch'])
    def status(self, request, username=None):
        user = self.get_object()
        r = {}
        if request.method == 'GET':
            r = {'status': user.get_status()}
        else:
            if not user.is_sudo_user(request):
                return Response({}, status=403)
            stat = request.DATA.get('status')
            status_choices = {
                    'active': user.set_active,
                    'disabled': user.set_disabled,
                    'deleted': user.set_deleted}
            status_choices[stat]()
        return Response(r, status=200)

    @action(methods=['post'])
    def changepassword(self, request, username=None):
        user = self.get_object()
        if not user.is_sudo_user(request):
            return Response({}, status=403)
        password = random_ldap_password()
        user.set_ldap_password(password)
        sms = SMS()
        message = "Your new {0} password: {1}".format(settings.COMPANY_NAME, password)
        response = sms.send(user.phone1 or user.phone2, message)
        if response.status_code in [200,201,202]:
            return Response('Password generated and sent', status=200)
        else:
            return Response('Password generated, but SMS failed', status=200)

    @action(methods=['post'])
    def addsshkey(self, request, username=None):
        user = self.get_object()
        if (request.user.username != user.username and
                not user.is_sudo_user(request)):
            return Response('Forbidden', status=403)

        ldap_data = user.ldap.fetch(user.get_dn(), filters=user.ldap_filter,
                attrs=['objectClass'], scope=ldap.SCOPE_BASE)
        if SSHKey.LDAP_OBJCLS not in ldap_data['objectClass']:
            user.ldap.op_modify(user.get_dn(),
                    [(ldap.MOD_ADD, 'objectClass', SSHKey.LDAP_OBJCLS)])

        with transaction.atomic():
            try:
                ssh_key = SSHKey(user=user, title=request.DATA['title'],
                        key=request.DATA['key'])
                ssh_key.save()
            except (sshpubkeys.InvalidKeyException, ValidationError) as e:
                return Response(str(e), status=status.HTTP_400_BAD_REQUEST)
            user.ldap.op_modify(user.get_dn(),
                    [(ldap.MOD_ADD, SSHKey.LDAP_ATTR, str(ssh_key.key))])

        changes_save(None, ssh_key, True)
        return Response('', status=200)

    @action(methods=['delete'])
    def deletesshkey(self, request, username=None):
        user = self.get_object()
        if (request.user.username != user.username and
                not user.is_sudo_user(request)):
            return Response('Forbidden', status=403)

        # LDAP controls SSH access to servers. If there's an error removing a
        # key from LDAP, fail and don't remove it from fum's DB.

        try:
            ssh_key = SSHKey.objects.get(
                    fingerprint=request.DATA['fingerprint'])
            user.ldap.op_modify(user.get_dn(),
                    [(ldap.MOD_DELETE, SSHKey.LDAP_ATTR, str(ssh_key.key))])
            ssh_key.delete()
        except Exception as e:
            return Response(str(e),
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        changes_delete(None, ssh_key)
        return Response('', status=200)

    def partial_update(self, request, username):
        try:
            viewsets.ModelViewSet.partial_update(self, request, username)
        except ValidationError as e:
            content = {'detail': ';'.join(e.messages)}
            return Response(content, status=status.HTTP_400_BAD_REQUEST)


class GroupsViewSet(ListMixin, LDAPViewSet):
    model = Groups
    serializer_class = GroupsSerializer
    lookup_field = 'name'
    list_serializer_class = GroupsListSerializer
    paginated_serializer_class = PaginatedGroupsSerializer
    
    @action(methods=['post', 'delete', 'get'])
    def users(self, request, name=None, relname=None):
        return mod_users(request, self.get_object().users, relname=relname)
        
class ServersViewSet(ListMixin, LDAPViewSet):
    model = Servers
    serializer_class = ServersSerializer
    lookup_field = 'name'
    list_serializer_class = ServersListSerializer
    paginated_serializer_class = PaginatedServersSerializer

    @action(methods=['post', 'delete', 'get'])
    def users(self, request, name=None, relname=None):
        return mod_users(request, self.get_object().users, relname=relname)

    @action(methods=['post', 'delete', 'get'])
    def sudoers(self, request, name=None, relname=None):
        return mod_users(request, self.get_object().sudoers, relname=relname)

class ProjectsViewSet(ListMixin, LDAPViewSet):
    model = Projects
    serializer_class = ProjectsSerializer
    lookup_field = 'name'
    list_serializer_class = ProjectsListSerializer
    paginated_serializer_class = PaginatedProjectsSerializer

    @action(methods=['post', 'delete', 'get'])
    def users(self, request, name=None, relname=None):
        return mod_users(request, self.get_object().users, relname=relname)
        
class EMailsViewSet(BaseViewSet):
    model = EMails
    serializer_class = EMailsSerializer
    lookup_field = 'address'

class EMailAliasesViewSet(BaseViewSet):
    model = EMailAliases
    serializer_class = AliasesSerializer
    lookup_field = 'address'

class SSHKeysViewSet(viewsets.ReadOnlyModelViewSet):
    model = SSHKey
    serializer_class = SSHKeysSerializer
    lookup_field = 'fingerprint'

def userphoto(request, username, size='thumb'):
    KEY = 'user-photo-url-%s-%s'%(username,size)
    url = cache.get(KEY)
    if not url:
        u = get_object_or_404(Users, username=username)
        SIZES = {
            'thumb': u.portrait_thumb_url,
            'full': u.portrait_full_url,
            'badge': u.portrait_badge_url,
        }
        url = SIZES.get(size, u.portrait_thumb_url)
        if not url:
            url = u.default_thumb_url()
        cache.set(KEY, url, 3600)
    return HttpResponseRedirect(url)

def list_employees(request):
    KEY = 'list-employees'
    data = cache.get(KEY)
    if data is None:
        groups = Groups.objects.filter(name__in=settings.EMPLOYEE_GROUPS)
        rs = []
        for group in groups:
            for user in group.users.all():
                if user.active_in_planmill:
                    user_data = UsersSerializer(user).data
                    if not filter(lambda x: x['id']==user_data['id'], rs):
                        rs.append(user_data)
        data = JSONRenderer().render(rs)
        cache.set(KEY, data, 1800)
    return HttpResponse(data, content_type='application/json')
