"""A collection of useful functions that didn't really belong anywhere else"""
from data_interrogator.interrogators import Allowable
from django.apps import apps


def get_all_base_models(bases):
    """From a beginning list of base_models, produce all reportable models"""
    all_models = {}

    if bases in [Allowable.ALL_MODELS, Allowable.ALL_APPS]:
        for app in apps.get_app_configs():
            for model in app.models:
                # (database field, human readable name)
                if app.verbose_name in all_models:
                    all_models[app.verbose_name] = (
                        all_models[app.verbose_name], (f'{app.name}:{model.__name__}', model.verbose_name)
                    )
                else:
                    all_models[app.verbose_name] = (
                        (f"{app.name}:{str(model.__name__)}", model.verbose_name),
                    )
        return list(all_models.items())

    for base in bases:
        if len(base) == 1:
            # If base_model is a app_name
            app_name = base[0]
            app = apps.get_app_config(app_name)

            for model in app.models:
                # (database field, human readable name)
                if app.verbose_name in all_models:
                    all_models[app.verbose_name] = (
                        all_models[app.verbose_name], (f"{app_name}:{model.__name__}", model.verbose_name)
                    )
                else:
                    all_models[app.verbose_name] = (
                        (f"{app_name}:{model.name}", model.verbose_name),
                    )
        else:
            # Base model is a (app_name, base_model) tuple
            app_name, model = base[:2]
            app = apps.get_app_config(app_name)
            model = app.get_model(model)
            if app.verbose_name in all_models:
                all_models[app.verbose_name] = (
                    all_models[app.verbose_name], (f"{app_name}:{str(model.__name__)}", model.verbose_name)
                )
            else:
                all_models[app.verbose_name] = ((f"{app_name}:{str(model.__name__)}", model.verbose_name),)

    all_models = list(all_models.items())
    return all_models
