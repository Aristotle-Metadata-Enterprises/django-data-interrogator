"""A collection of useful functions that didn't really belong anywhere else"""
import re
from enum import Enum
from typing import Tuple, Union

from django.apps import apps
from django.conf import settings
from django.db.models import DurationField, ExpressionWrapper, F, FloatField, Model

from data_interrogator.db import DateDiff, ForceDate

import logging

logger = logging.getLogger(__name__)
logger.debug(f"Logging started for {__name__}")


# Utility functions
math_infix_symbols = {
    '-': lambda a, b: a - b,
    '+': lambda a, b: a + b,
    '/': lambda a, b: a / b,
    '*': lambda a, b: a * b,
}


class Allowable(Enum):
    ALL_APPS = 1
    ALL_MODELS = 1
    ALL_FIELDS = 3



def normalise_field(text) -> str:
    """Replace the UI access with the backend Django access"""
    return text.strip().replace('(', '::').replace(')', '').replace(".", "__")


def is_math_expression(expression):
    return any(s in expression for s in math_infix_symbols.keys())


def normalise_math(expression):
    """Normalise math from UI """
    if not is_math_expression(expression):
        # we're aggregating some mathy things, these are tricky
        return F(normalise_field(expression))

    math_operator_re = '[\-\/\+\*]'

    a, b = [v.strip() for v in re.split(math_operator_re, expression, 1)]
    first_operator = re.findall(math_operator_re, expression)[0]

    if first_operator == "-" and a.endswith('date') and b.endswith('date'):
        expr = ExpressionWrapper(
            DateDiff(
                ForceDate(F(a)),
                ForceDate(F(b))
            ), output_field=DurationField()
        )
    else:
        expr = ExpressionWrapper(
            math_infix_symbols[first_operator](F(a), F(b)),
            output_field=FloatField()
        )
    return expr


def get_human_readable_model_name(model: Model) -> str:
    """Get the optimal model name from a model"""
    if type(model) == str:
        return model

    name = f'{model._meta.app_label}:{model.__name__}'

    if hasattr(settings, 'INTERROGATOR_NAME_OVERRIDES') and name in settings.INTERROGATOR_NAME_OVERRIDES:
        return settings.INTERROGATOR_NAME_OVERRIDES[name]
    elif hasattr(model, 'interrogator_name'):
        return getattr(model, 'interrogator_name')
    else:
        return model._meta.verbose_name.title()


def append_to_group(app_group, app_model_pair) -> Tuple:
    app_group = list(app_group)
    app_group.append(app_model_pair)

    return tuple(app_group)


def get_model_name(model: Union[str, Model]):
    if type(model) != str:
        return model.__name__
    return model


def get_all_base_models(bases):
    """From a beginning list of base_models, produce all reportable models"""
    all_models = {}

    if bases in [Allowable.ALL_MODELS, Allowable.ALL_APPS]:
        for app in apps.get_app_configs():
            for model in app.models:
                model_name = get_model_name(model)
                human_readable_name = get_human_readable_model_name(model)

                if app.verbose_name in all_models:
                    all_models[app.verbose_name] = append_to_group(
                        all_models[app.verbose_name],
                        tuple([f'{app.name}:{model_name}', human_readable_name])
                    )
                else:
                    all_models[app.verbose_name] = (
                        (f"{app.name}:{model_name}", human_readable_name),
                    )
        return list(all_models.items())

    for base in bases:
        if len(base) == 1:
            # If base_model is a app_name
            app_name = base[0]
            app = apps.get_app_config(app_name)

            for model in app.models:
                # (database field, human readable name)
                model_name = get_model_name(model)
                human_readable_name = get_human_readable_model_name(model)

                if app.verbose_name in all_models:

                    all_models[app.verbose_name] = append_to_group(
                        all_models[app.verbose_name],
                        tuple([f"{app_name}:{model_name}", human_readable_name])
                    )
                else:
                    all_models[app.verbose_name] = (
                        (f"{app_name}:{model_name}", human_readable_name)
                    )
        else:
            # Base model is a (app_name, base_model) tuple
            app_name, model = base[:2]
            app = apps.get_app_config(app_name)
            model = app.get_model(model)

            model_name = get_model_name(model)
            human_readable_name = get_human_readable_model_name(model)

            if app.verbose_name in all_models:
                all_models[app.verbose_name] = append_to_group(
                    all_models[app.verbose_name],
                    tuple([f"{app_name}:{model_name}", human_readable_name])
                )
            else:
                all_models[app.verbose_name] = tuple(
                    [(f"{app_name}:{model_name}", human_readable_name)]
                )

    all_models = list(all_models.items())
    return all_models


def table_view(qs, values, padding=15):
    data = qs.values(*values)
    print("| ".join(
        [f"{v}\t".expandtabs(padding) for v in values]
    ))
    for data in qs.values_list(*values):
        print("| ".join([f"{v}\t".expandtabs(padding) for v in data]))
