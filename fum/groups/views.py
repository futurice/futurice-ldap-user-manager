from django.shortcuts import redirect
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView
from django.views.generic import ListView, DetailView
from django.views.generic.edit import FormView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponse

from fum.models import Users, Groups, Servers
from fum.util import append_crud_urls
from fum.common.views import filter_by_permissions

from forms import GroupsForm
import json

NAME = 'groups'
MODEL = Groups

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
    form_klass = GroupsForm

    def form_valid(self, form):
        # This method is called when valid form data has been POSTed.
        # It should return an HttpResponse.
        #form.send_email()
        return super(View, self).form_valid(form)

class Create(CreateView):
    template_name = '%s/%s_form.html'%(NAME,NAME)
    model = MODEL
    form_class = GroupsForm

class Update(UpdateView):
    template_name = '%s/%s_form.html'%(NAME,NAME)
    model = MODEL
    form_class = GroupsForm

    def form_valid(self, form):
        if 'join' in self.request.POST:
            user = Users.objects.get(username = self.request.META['REMOTE_USER'])
            self.object.users.add(user)
            return redirect(self.object)
        else:
            return super(Update, self).form_valid(form)


def groups_json(request):
    user = Users.objects.get(username=request.META['REMOTE_USER'])
    try:
        q = request.GET['q']
        filtered = Groups.objects.filter(name__icontains=q) 
        groups = [] 
        for group in filter_by_permissions(request, user, filtered.distinct()):
            json_group={}
            json_group['name'] = group.name
            groups.append(json_group)
    except KeyError:
        groups = [group.name for group in filter_by_permissions(request, user, Groups.objects.all())]
    return HttpResponse(json.dumps(groups), content_type='application/json')

def group_detail_json(request, pk):
    group = get_object_or_404(Groups, name=pk)
    users = [k['username'] for k in group.users.all().order_by().values('username')]
    return HttpResponse(json.dumps(users), content_type='application/json')
