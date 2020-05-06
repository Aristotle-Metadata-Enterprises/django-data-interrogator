from django import forms

from data_interrogator.fields import CSVMultipleCharField
from data_interrogator.forms import PivotTableForm, InterrogatorTableForm


class AdminPivotTableForm(PivotTableForm):
    column_1 = forms.CharField()
    column_2 = forms.CharField()
    aggregators = CSVMultipleCharField(required=False)
    filter_by = CSVMultipleCharField(required=False)


class AdminInvestigationForm(InterrogatorTableForm):
    filter_by = CSVMultipleCharField(required=False)
    columns = CSVMultipleCharField()
    sort_by = CSVMultipleCharField(required=False)
