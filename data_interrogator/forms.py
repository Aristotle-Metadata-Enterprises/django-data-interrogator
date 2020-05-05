from django import forms
from django.apps import apps

from data_interrogator.fields import CSVMultipleCharField
from data_interrogator.interrogators import allowable


class InterrogatorForm(forms.Form):
    lead_base_model = forms.ChoiceField(choices=[], required=True, label="Initial object")

    def __init__(self, *args, interrogator, **kwargs):
        super(InterrogatorForm, self).__init__(*args, **kwargs)
        self.interrogator = interrogator
        self.fields['lead_base_model'].choices = self.base_models

    @property
    def base_models(self):
        base_models = self.interrogator.report_models

        BASE_MODELS = []
        if base_models in [allowable.ALL_MODELS, allowable.ALL_APPS]:
            return [
                ("%s:%s" % (app.name, model), model.title())
                for app in apps.app_configs.values()
                for model in app.models
            ]

        for base_model in base_models:
            if len(base_model) == 1:
                app_name = base_model[0]
                for model in apps.get_app_config(app_name).models:
                    BASE_MODELS.append(("%s:%s" % (app_name, model), model))
            else:
                app, model = base_model[:2]
                BASE_MODELS.append(("%s:%s" % (app, model), model))
        return BASE_MODELS


class InterrogatorTableForm(InterrogatorForm):
    filter_by = CSVMultipleCharField()
    columns = CSVMultipleCharField()
    sort_by = CSVMultipleCharField()


class InvestigationForm(InterrogatorTableForm):
    pass


class PivotTableForm(InterrogatorForm):
    filter_by = CSVMultipleCharField(required=False)
    column_1 = forms.CharField()
    column_2 = forms.CharField()
    aggregators = CSVMultipleCharField(required=False)
