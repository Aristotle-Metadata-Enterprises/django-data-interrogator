"""A collection of useful functions that didn't really belong anywhere else"""
from data_interrogator.interrogators import Allowable
from django.apps import apps


def get_all_base_models(base_models):
    """From a beginning list of base_models, produce all possible navigable business models"""
    all_models = []

    if base_models in [Allowable.ALL_MODELS, Allowable.ALL_APPS]:
        all_models = [
            ("%s:%s" % (app.name, model), model.title())
            for app in apps.app_configs.values()
            for model in app.models
        ]
        return all_models

    for base_model in base_models:
        if len(base_model) == 1:
            app_name = base_model[0]
            for model in apps.get_app_config(app_name).models:
                all_models.append(("%s:%s" % (app_name, model), model))
        else:
            app, model = base_model[:2]
            all_models.append(("%s:%s" % (app, model), model))
    return all_models
