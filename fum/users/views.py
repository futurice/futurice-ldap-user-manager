from django.views.generic import TemplateView
from django.views.generic import ListView, DetailView
from django.views.generic.edit import FormView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponse
from django.db.models import Q


from fum.models import Users, Groups, Servers
from fum.util import append_crud_urls
import os, json

from forms import UsersForm, CustomerForm

NAME = 'users'
MODEL = Users

class ListView(ListView):
    model = MODEL
    template_name = '%s/%s_list.html'%(NAME,NAME)
    
    # Order by case-insensitive name (because Postgre)
    def get_queryset(self):
        return self.model.objects.all().extra(select={'lower_name': 'lower(first_name)||\' \'||lower(last_name)'}).order_by('lower_name')

    def get_context_data(self, **kwargs):
        context = super(ListView, self).get_context_data(**kwargs)
        append_crud_urls(context, NAME)
        return context

class DetailView(DetailView):
    template_name = '%s/%s_detail.html'%(NAME,NAME)
    model = MODEL
    slug_field = 'username'
    
    def get_context_data(self, **kwargs):
        context = super(DetailView, self).get_context_data(**kwargs)
        return context

class Create(CreateView):
    template_name = '%s/%s_form.html'%(NAME,NAME)
    model = MODEL

    def get(self, request, *args, **kwargs):
        self.form_class = UsersForm if bool(request.session.get('sudo_timeout', False)) else CustomerForm
        self.object = None
        return super(CreateView, self).get(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy('users_detail', kwargs={'slug': self.object.username})

def users_json(request):
    try:
        q = request.GET['q']
        search_terms = q.split()

        filtered = Users.objects
        for word in search_terms:
            filtered = filtered.filter(Q(first_name__icontains=word) | Q(last_name__icontains=word) | Q(username__icontains=word)) 
        
        users = [] 
        for user in filtered.distinct():
            json_user={}
            json_user['username'] = user.username
            json_user['first_name'] = user.first_name
            json_user['last_name'] = user.last_name
            users.append(json_user)
    except KeyError:
        users = [user.username for user in Users.objects.all()]
    return HttpResponse(json.dumps(users), content_type='application/json')
