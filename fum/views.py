from django.conf import settings
from django.views.generic import TemplateView
from django.shortcuts import redirect
from django.shortcuts import get_object_or_404

from fum.models import Users

class IndexView(TemplateView):
    template_name = "index.html"
    
    def get(self, request):
        user = get_object_or_404(Users, username=request.META.get('REMOTE_USER','tsyr'))
        return redirect(user)
