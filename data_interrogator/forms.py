from django import forms

from data_interrogator.fields import CSVMultipleCharField
from data_interrogator.utils import get_all_base_models


class InterrogatorForm(forms.Form):
    lead_base_model = forms.ChoiceField(choices=[], required=True, label="Initial object")

    def __init__(self, *args, interrogator, **kwargs):
        super(InterrogatorForm, self).__init__(*args, **kwargs)
        self.interrogator = interrogator
        self.fields['lead_base_model'].choices = self.base_models

    @property
    def base_models(self):
        return get_all_base_models(self.interrogator.report_models)


class InterrogatorTableForm(InterrogatorForm):
    filter_by = CSVMultipleCharField(required=False)
    columns = CSVMultipleCharField()
    sort_by = CSVMultipleCharField(required=False)
    limit = forms.IntegerField(required=False)


class InvestigationForm(InterrogatorTableForm):
    pass


class PivotTableForm(InterrogatorForm):
    filter_by = CSVMultipleCharField(required=False)
    column_1 = forms.CharField()
    column_2 = forms.CharField()
    aggregators = CSVMultipleCharField(required=False)
