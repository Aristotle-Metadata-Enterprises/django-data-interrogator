from django import forms

from django.conf import settings
from django.template.loader import get_template
from django.template import Context
from django.utils.translation import ugettext_lazy as _

from data_interrogator.fields import MultipleCharField
from data_interrogator.models import DataTablePage

suspects = getattr(settings, 'DATA_INTERROGATION_DOSSIER', {}).get('suspects',[])

SUSPECTS = []
for suspect in suspects:
    app,model = suspect['model']
    SUSPECTS.append(("%s:%s"%(app,model),model))

class InvestigationForm(forms.Form):
    lead_suspect = forms.ChoiceField(choices=SUSPECTS,required=True,label="Initial object")
    #filter_by = forms.CharField(label='Filter by', max_length=100, required=False)
    filter_by = MultipleCharField(extra=1,required=False, add_text="Add filter", remove_title="Remove filter", remove_text="-")
    columns = MultipleCharField(extra=2,required=False, add_text="Add column", remove_title="Remove column", remove_text="-")
    sort_by = MultipleCharField(extra=1,required=False, add_text="Add ordering", remove_title="Remove ordering", remove_text="-")
    #sort_by = forms.CharField(label='Sort by', max_length=100, required=False)

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
        model = DataTablePage
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

from django.contrib.contenttypes.models import ContentType
LIST_OF_MODELS = [ ("%s:%s"%(m.app_label,m.model),"%s:%s"%(m.app_label,m.model))
                    for m in ContentType.objects.all()]

class UploaderForm(forms.Form):
    main_model = forms.ChoiceField(choices=LIST_OF_MODELS,required=True,label="Main model")
    delimiter = forms.ChoiceField(choices=[('comma','comma'),('tab','tab'),('other','other')],required=True,label="Delimiter",help_text='The character used to indicate separate columns in the file.')
    other_delimiter = forms.CharField(required=False,label="Other delimiter",help_text="Only add if 'other' is selected above")
    data_file = forms.FileField(required=True,label="Data file to upload")
#    line_from = forms.PositiveIntegerField(required=True,label="Line to start processing from. Optional, default '0'.")
#    line_to = forms.PositiveIntegerField(required=True,label="Line to finish processing on. Optional, default process all lines.")
#    line_to = forms.PositiveIntegerField(required=True,label="Line to finish processing on. Optional, default process all lines.")
