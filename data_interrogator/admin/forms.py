from django import forms
from django.apps import apps

from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from data_interrogator.forms import InterrogatorForm, PivotTableForm, InterrogatorTableForm
from data_interrogator.fields import CSVMultipleCharField


class AdminPivotTableForm(PivotTableForm):
    column_1 = forms.CharField()
    column_2 = forms.CharField()
    aggregators = CSVMultipleCharField(required=False)
    filter_by = CSVMultipleCharField(required=False)


class AdminInvestigationForm(InterrogatorTableForm):
    filter_by = CSVMultipleCharField(required=False)
    columns = CSVMultipleCharField()
    sort_by = CSVMultipleCharField(required=False)
