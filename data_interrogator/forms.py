from django import forms

from django.conf import settings
from django.template.loader import get_template
from django.template import Context
from django.utils.translation import ugettext_lazy as _

from data_interrogator import models
from data_interrogator.fields import MultipleCharField, AdminMultipleCharInput


class InterrogatorForm(forms.Form):
    lead_suspect = forms.ChoiceField(choices=[],required=True,label="Initial object")
    def __init__(self, *args, **kwargs):
        super(InterrogatorForm, self).__init__(*args, **kwargs)
        self.fields['lead_suspect'].choices = self.suspects

    @property
    def suspects(self):
        suspects = getattr(settings, 'DATA_INTERROGATION_DOSSIER', {}).get('suspects',[])
        
        SUSPECTS = []
        for suspect in suspects:
            app,model = suspect['model']
            SUSPECTS.append(("%s:%s"%(app,model),model))
        return SUSPECTS


class InterrogatorTableForm(InterrogatorForm):
    filter_by = MultipleCharField(extra=1,required=False, add_text="Add filter", remove_title="Remove filter", remove_text="-")
    columns = MultipleCharField(extra=2,required=False, add_text="Add column", remove_title="Remove column", remove_text="-")
    sort_by = MultipleCharField(extra=1,required=False, add_text="Add ordering", remove_title="Remove ordering", remove_text="-")


class AdminInvestigationForm(InterrogatorTableForm):
    lead_suspect = forms.ChoiceField(choices=[],required=True,label="Base query object")
    def __init__(self, *args, **kwargs):
        super(AdminInvestigationForm, self).__init__(*args, **kwargs)
        self.fields['filter_by'].widget = AdminMultipleCharInput()
        self.fields['columns'].widget = AdminMultipleCharInput()
        self.fields['sort_by'].widget = AdminMultipleCharInput()


class InvestigationForm(InterrogatorTableForm):
    pass


class PivotTableForm(InterrogatorForm):
    filter_by = MultipleCharField(extra=1,required=False, add_text="Add filter", remove_title="Remove filter", remove_text="-")
    column_1 = forms.CharField()
    column_2 = forms.CharField()
    aggregators = MultipleCharField(extra=1,required=False, add_text="Add column", remove_title="Remove column", remove_text="-")

class AdminPivotTableForm(PivotTableForm):
    def __init__(self, *args, **kwargs):
        super(AdminPivotTableForm, self).__init__(*args, **kwargs)
        self.fields['filter_by'].widget = AdminMultipleCharInput()
        self.fields['aggregators'].widget = AdminMultipleCharInput()

class DataTablePageForm(forms.ModelForm):
    url = forms.RegexField(label=_("URL"), max_length=100, regex=r'^[-\w/\.~]+$',
        help_text=_("Example: '/about/contact/'. Make sure to have leading"
                    " and trailing slashes."),
        error_messages={
            "invalid": _("This value must contain only letters, numbers,"
                         " dots, underscores, dashes, slashes or tildes."),
        },
    )
    class Meta:
        model = models.DataTablePage
        fields = '__all__'

    def clean_url(self):
        url = self.cleaned_data['url']
        if not url.startswith('/'):
            raise forms.ValidationError(
                _("URL is missing a leading slash."),
                code='missing_leading_slash',
            )
        if (settings.APPEND_SLASH and
                'django.middleware.common.CommonMiddleware' in settings.MIDDLEWARE_CLASSES and
                not url.endswith('/')):
            raise forms.ValidationError(
                _("URL is missing a trailing slash."),
                code='missing_trailing_slash',
            )
        return url

    def clean(self):
        url = self.cleaned_data.get('url')

        same_url = DataTablePage.objects.filter(url=url)
        if self.instance.pk:
            same_url = same_url.exclude(pk=self.instance.pk)

        if same_url.exists():
            raise forms.ValidationError(
                _('Data page with url %(url)s already exists'),
                code='duplicate_url',
                params={'url': url},
            )

        return super(DataTablePageForm, self).clean()

class UploaderForm(forms.Form):

    main_model = forms.ChoiceField(choices=[],required=True,label="Main model")
    separator = forms.ChoiceField(choices=[('comma','comma'),('tab','tab'),('other','other')],required=True,label="Delimiter",help_text='The character used to indicate separate columns in the file.')
    other_separator = forms.CharField(required=False,label="Other separator",help_text="Only add if 'other' is selected above")
    #create_or_update = forms.ChoiceField(choices=[('create','create'),('update','update')],required=True,label="Update or create",help_text='')
    update_keys = forms.CharField(required=False,help_text="Specify a comma separated list of headers in file used to identify objects to update with the other values. If left blank new records will be created if any fields differ from those in the database.")
    data_file = forms.FileField(required=True,label="Data file to upload")
#    line_from = forms.PositiveIntegerField(required=True,label="Line to start processing from. Optional, default '0'.")
#    line_to = forms.PositiveIntegerField(required=True,label="Line to finish processing on. Optional, default process all lines.")

    def __init__(self, *args, **kwargs):
        super(UploaderForm,self).__init__(*args, **kwargs)
        from django.contrib.contenttypes.models import ContentType
        LIST_OF_MODELS = [ ("%s.%s"%(m.app_label,m.model),"%s.%s"%(m.app_label,m.model))
                        for m in ContentType.objects.all()]

        #self.fields['main_model'] = forms.ChoiceField(choices=LIST_OF_MODELS)
        self.fields['main_model'].choices = LIST_OF_MODELS
            