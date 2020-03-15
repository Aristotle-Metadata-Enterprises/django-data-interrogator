from django import forms

from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from data_interrogator import models
from data_interrogator.fields import CSVMultipleCharField


class InterrogatorForm(forms.Form):
    lead_base_model = forms.ChoiceField(choices=[],required=True,label="Initial object")
    def __init__(self, *args, interrogator, **kwargs):
        super(InterrogatorForm, self).__init__(*args, **kwargs)
        self.interrogator = interrogator
        self.fields['lead_base_model'].choices = self.base_models

    @property
    def base_models(self):
        base_models = self.interrogator.report_models
        
        BASE_MODELS = []
        for base_model in base_models:
            app,model = base_model[:2] #'model']
            BASE_MODELS.append(("%s:%s"%(app,model),model))
        return BASE_MODELS


class InterrogatorTableForm(InterrogatorForm):
    filter_by = CSVMultipleCharField()
    columns = CSVMultipleCharField()
    sort_by = CSVMultipleCharField()

#
# class AdminInvestigationForm(InterrogatorTableForm):
#     lead_base_model = forms.ChoiceField(choices=[],required=True,label="Base query object")
#     def __init__(self, *args, **kwargs):
#         super(AdminInvestigationForm, self).__init__(*args, **kwargs)
#         self.fields['filter_by'].widget = AdminMultipleCharInput()
#         self.fields['columns'].widget = AdminMultipleCharInput()
#         self.fields['sort_by'].widget = AdminMultipleCharInput()
#

class InvestigationForm(InterrogatorTableForm):
    pass


class PivotTableForm(InterrogatorForm):
    filter_by = CSVMultipleCharField(required=False)
    column_1 = forms.CharField()
    column_2 = forms.CharField()
    aggregators = CSVMultipleCharField(required=False)

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
