"""A collection of useful functions that didn't really belong anywhere else"""
from data_interrogator.interrogators import Allowable
from django.apps import apps
from django.db.models import Model

from typing import Tuple
import logging

logger = logging.getLogger(__name__)
logger.debug(f"Logging started for {__name__}")


def get_optimal_model_name(model: Model) -> str:
    """Get the optimal model name from a model"""
    if hasattr(model, 'interrogator_name'):
        return getattr(model, 'interrogator_name')
    elif hasattr(model, 'verbose_name'):
        return getattr(model, 'verbose_name')
    else:
        return model.__name__.title()


def append_to_group(app_group, app_model_pair) -> Tuple:
    app_group = list(app_group)
    app_group.append(app_model_pair)

    return tuple(app_group)


def get_all_base_models(bases):
    """From a beginning list of base_models, produce all reportable models"""
    all_models = {}

    if bases in [Allowable.ALL_MODELS, Allowable.ALL_APPS]:
        for app in apps.get_app_configs():
            for model in app.models:
                # (database field, human readable name)
                if app.verbose_name in all_models:
                    all_models[app.verbose_name] = append_to_group(
                        all_models[app.verbose_name], tuple([f'{app.name}:{model.__name__}', get_optimal_model_name(model)])
                    )
                else:
                    all_models[app.verbose_name] = (
                        (f"{app.name}:{str(model.__name__)}", get_optimal_model_name(model)),
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
                    all_models[app.verbose_name] = append_to_group(
                        all_models[app.verbose_name], tuple([f"{app_name}:{model.__name__}", get_optimal_model_name(model)])
                    )
                else:
                    all_models[app.verbose_name] = (
                        (f"{app_name}:{model.name}", get_optimal_model_name(model)),
                    )
        else:
            # Base model is a (app_name, base_model) tuple
            app_name, model = base[:2]
            app = apps.get_app_config(app_name)
            model = app.get_model(model)
            if app.verbose_name in all_models:
                all_models[app.verbose_name] = append_to_group(
                    all_models[app.verbose_name], tuple([f"{app_name}:{str(model.__name__)}", get_optimal_model_name(model)])
                )
            else:
                all_models[app.verbose_name] = tuple([(f"{app_name}:{str(model.__name__)}", get_optimal_model_name(model))])

    all_models = list(all_models.items())
    return all_models
