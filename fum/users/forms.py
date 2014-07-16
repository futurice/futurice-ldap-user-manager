from django.forms import ModelForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout,Fieldset, HTML, Field
from crispy_forms.bootstrap import FormActions

from fum.models import Users

class UsersForm(ModelForm):


    def __init__(self, *args, **kwargs):
        super(UsersForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_id = 'create-user-form'
        self.helper.form_method = 'post'
        self.helper.form_action = 'users_add'
        self.helper.form_tag = True
        self.helper.layout = Layout(
            Fieldset(
                'Create a new user.',
                HTML("""
                    <select id="user-type-selector">
                        <option value="-1" selected="selected">--</option>
                        <option value="2001">Internal</option> 
                        <option value="2002">External</option>
                        <option value="2003">Customer</option>
                    </select>
                    """),
                'first_name',
                'last_name',
                'username',
                'title',
                HTML("""
                    <div id="div_id_email" class="control-group">
                        <label for="id_email" class="control-label">Email</label>
                        <div class="controls"><input class="textinput textInput" id="id_email" name="email" type="email">
                        </div>
                    </div>
                """),
                Field('phone1', type='tel'),
                Field('phone2', type='tel'),
                'skype',
                'google_status',
                ),
            FormActions(
                Submit('submit', 'Create')
                )
        )

    class Meta:
        model=Users
        exclude=('password_expires_date',)
    
class CustomerForm(ModelForm):


    def __init__(self, *args, **kwargs):
        super(CustomerForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_id = 'create-user-form'
        self.helper.form_method = 'post'
        self.helper.form_action = 'users_add'
        self.helper.form_tag = True
        self.helper.layout = Layout(
            Fieldset(
                'Create a new customer. To create a new Internal/External IT access required.',
                HTML("""
                    <input id="user-type-selector" type="hidden" value="2003">
                    """),
                'first_name',
                'last_name',
                'username',
                'title',
                HTML("""
                    <div id="div_id_email" class="control-group">
                        <label for="id_email" class="control-label">Email</label>
                        <div class="controls"><input class="textinput textInput" id="id_email" name="email" type="email">
                        </div>
                    </div>
                """),
                Field('phone1', type='tel'),
                Field('phone2', type='tel'),
                'skype',
                ),
            FormActions(
                Submit('submit', 'Create')
                )
        )

    class Meta:
        model=Users
        exclude=('password_expires_date',)
    
