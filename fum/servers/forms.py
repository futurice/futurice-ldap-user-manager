from django.forms import ModelForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout,Fieldset, HTML, Field
from crispy_forms.bootstrap import FormActions

from fum.models import Servers

class ServersForm(ModelForm):


    def __init__(self, *args, **kwargs):
        super(ServersForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_id = 'create-server-form'
        self.helper.form_method = 'post'
        self.helper.form_tag = True
        self.helper.layout = Layout(
            Fieldset(
                'Create a new group.',
                'name',
                'description',
                Field('editor_group', css_class="chosen-select"),
                ),
            FormActions(
                Submit('submit', 'Create')
                )
        )

    class Meta:
        model=Servers
        exclude=('object_id', 'content_type', 'users')