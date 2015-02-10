#from __future__ import print_function
from django.conf import settings
from django.http import Http404
from django.views.generic import TemplateView
from django.shortcuts import redirect
from django.core import serializers
from django.forms.models import model_to_dict
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from haystack.query import SearchQuerySet
from haystack.inputs import Raw

from rest_framework import status

from datetime import datetime, timedelta
import pysolr
import json

from fum.ldap_helpers import test_user_ldap
from fum.models import Users
from .util import to_json

import logging

log = logging.getLogger(__name__)

def query(q, limit=None):
    if not q:
        return []
    limit = getattr(settings, 'HAYSTACK_MAX_RESULTS', 25)
    return SearchQuerySet().using('default').filter(content=Raw(q))[:limit]

class SearchView(TemplateView):
    template_name = "common/search_all.html"
    def get(self, request, *args, **kwargs):
        # do separata queries to keep ranking working
        search_query = request.GET.get(u'q', '').strip()
        search_query = '*%s*'%search_query
        result = query(search_query)
        
        # group, and do db_queries?
        if request.is_ajax():
            r = []
            for item in result:
                obj = item.object
                if not obj:
                    continue
                i = {}
                try:
                    i['name'] = "%s %s"%(obj.first_name, obj.last_name)
                    i['id'] = obj.username
                except AttributeError:
                    i['name'] = obj.name
                    i['id'] = i['name']

                i['type'] = item.model_name
                i['url'] = item.object.get_absolute_url()
                r.append(i)
            return HttpResponse(to_json(r), content_type='application/json')
        else:
            context = {'search_query': search_query,
                    'result': result}
            return self.render_to_response(context)
        
def enable_superuser(request):
    if request.is_ajax():
        response = {}

        now = datetime.utcnow()

        # Check if not valid
        timeout = request.session.get('sudo_timeout', None)

        if timeout is not None and timeout < now:
            request.session.pop('sudo_timeout')
            response['desc'] = 'Sudoer timeout, please refresh.'
            return HttpResponse(json.dumps(response),
                    status=status.HTTP_401_UNAUTHORIZED,
                    content_type='application/json')

        if timeout is None:
            try:
                password = request.REQUEST['password']
            except KeyError: 
                response['desc'] = 'No password in form.'
                return HttpResponse(json.dumps(response), status=400, content_type='application/json')
        
            user = Users.objects.get(username=request.user.username)
            if not (user.is_in_teamit() and test_user_ldap(user.username, password)):
                response['desc'] = 'Incorrect password or unauthorized user.'
                return HttpResponse(json.dumps(response), status=401, content_type='application/json')

        # Session was valid or password was correct, start/renew session
        endtime = datetime.utcnow() + timedelta(minutes=settings.SUDO_TIMEOUT)
        request.session['sudo_timeout'] = endtime
        # Hack to avoid timezone problems
        response['desc'] = (endtime+(datetime.now()-datetime.utcnow())).strftime('%s')
        return HttpResponse(json.dumps(response), status=200, content_type='application/json')

    return HttpResponse('Not passing Django HTTPRequest.is_ajax() check, ' +
            'i.e. HTTP_X_REQUESTED_WITH XMLHttpRequest',
            status=status.HTTP_400_BAD_REQUEST)

def end_superuser(request):
    if request.is_ajax():
        response = {}

        if request.session.get('sudo_timeout', None) is not None:
            request.session.pop('sudo_timeout')

        response['desc'] = 'Sudo mode ended.'
        return HttpResponse(json.dumps(response), status=200, content_type='application/json')

def filter_by_permissions(request, user, groups):
    groups_filtered = []
    for group in groups:
        if user.is_sudo_user(request) or group.editor_group is None or user.in_group(group.editor_group):
            groups_filtered.append(group)
    return groups_filtered
