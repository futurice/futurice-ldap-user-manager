from django.shortcuts import redirect
from django.views.generic import TemplateView
from django.views.generic import ListView, DetailView
from django.views.generic.edit import FormView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponse

from fum.models import Users, Groups, Servers
from fum.util import append_crud_urls
from fum.common.views import filter_by_permissions
from fum.servers.forms import ServersForm

import json

NAME = 'servers'
MODEL = Servers

class ListView(ListView):
    model = MODEL
    template_name = '%s/%s_list.html'%(NAME,NAME)

    # Order by case-insensitive name (because Postgre)
    def get_queryset(self):
        return self.model.objects.all().extra(select={'lower_name': 'lower(name)'}).order_by('lower_name')

    def get_context_data(self, **kwargs):
        context = super(ListView, self).get_context_data(**kwargs)
        append_crud_urls(context, NAME)
        return context

class DetailView(DetailView):
    template_name = '%s/%s_detail.html'%(NAME,NAME)
    model = MODEL
    slug_field = 'name'

    def get_context_data(self, **kwargs):
        context = super(DetailView, self).get_context_data(**kwargs)
        return context

class View(FormView):
    success_url = '/%s/'%NAME

    def form_valid(self, form):
        # This method is called when valid form data has been POSTed.
        # It should return an HttpResponse.
        #form.send_email()
        return super(View, self).form_valid(form)

class Create(CreateView):
    template_name = '%s/%s_form.html'%(NAME,NAME)
    model = MODEL
    form_class = ServersForm

class Update(UpdateView):
    template_name = '%s/%s_form.html'%(NAME,NAME)
    model = MODEL

    def form_valid(self, form):
        if 'join' in self.request.POST:
            user = Users.objects.get(username = self.request.META['REMOTE_USER'])
            self.object.users.add(user)
        elif 'join_sudoers' in self.request.POST:
            user = Users.objects.get(username = self.request.META['REMOTE_USER'])
            self.object.sudoers.add(user)
        else:
            return super(Update, self).form_valid(form)
        return redirect(self.object)

def servers_json(request):
    user = Users.objects.get(username = request.META['REMOTE_USER'])
    try:
        q = request.GET['q']
        q = q.strip()
        filtered = Servers.objects.filter(name__icontains=q) 
        servers = [] 
        for server in filter_by_permissions(request, user, filtered.distinct()):
            json_server={}
            json_server['name'] = server.name
            servers.append(json_server)
    except KeyError:
        servers = [server.name for server in filter_by_permissions(request, user, Servers.objects.all())]
    return HttpResponse(json.dumps(servers), content_type='application/json')

def server_detail_json(request, servername):
    server = get_object_or_404(Groups, name=groupname)
    users = [user.username for user in server.users.all()]
    return HttpResponse(json.dumps(users), content_type='application/json')
