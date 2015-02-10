from django.conf import settings
from django.views.generic import TemplateView
from django.shortcuts import redirect
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from fum.models import Users

class IndexView(TemplateView):
    template_name = "index.html"
    
    @method_decorator(login_required)
    def get(self, request):
        user = get_object_or_404(Users, username=request.user.username)
        return redirect(user)
