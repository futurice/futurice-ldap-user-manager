from django.forms import ModelForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout,Fieldset, HTML, Field
from crispy_forms.bootstrap import FormActions

from fum.models import Projects

class ProjectsForm(ModelForm):


    def __init__(self, *args, **kwargs):
        super(ProjectsForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_id = 'create-project-form'
        self.helper.form_method = 'post'
        self.helper.form_tag = True
        self.helper.layout = Layout(
            Fieldset(
                'Create a new project.',
                'name',
                'description',
                Field('editor_group', css_class="chosen-select"),
                ),
            FormActions(
                Submit('submit', 'Create')
                )
        )

    class Meta:
        model=Projects
        exclude=('object_id', 'content_type', 'users')