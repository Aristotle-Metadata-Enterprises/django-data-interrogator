import django.db.models
import django.db.models.functions
from django.db.models import functions as func
from django.db.models import Count, Min, Max, Sum, Value, Avg
from data_interrogator.db import GroupConcat, DateDiff, ForceDate, SumIf, ComplexLookup
from data_interrogator import exceptions as di_exceptions

from data_interrogator.utils import normalise_field, normalise_math


aggregate_register = {}
def register_aggregator(Aggregate):
    if Aggregate.command in aggregate_register.keys():
        raise di_exceptions.DuplicateAnnotationCommand(Aggregate, aggregate_register[Aggregate.command])
    else:
        aggregate_register[Aggregate.command] = Aggregate
    return Aggregate


class InterrogatorFunction:
    def process_arguments(self, argument_string):
        argument_string = normalise_math(argument_string)
        return [argument_string], {"distinct": False}

    def as_django(self, argument_string):
        args, kwargs = self.process_arguments(argument_string)
        return self.aggregator(*args, **kwargs)


@register_aggregator
class Max(InterrogatorFunction):
    command = "max"
    aggregator = django.db.models.Max


@register_aggregator
class Min(InterrogatorFunction):
    command = "Min"
    aggregator = django.db.models.Min



@register_aggregator
class Sum(InterrogatorFunction):
    command = "sum"
    aggregator = django.db.models.Sum



@register_aggregator
class Avg(InterrogatorFunction):
    command = "avg"
    aggregator = django.db.models.Avg



@register_aggregator
class Count(InterrogatorFunction):
    command = "count"
    aggregator = django.db.models.Count



@register_aggregator
class GroupConcat(InterrogatorFunction):
    command = "group"
    aggregator = GroupConcat



@register_aggregator
class Substr(InterrogatorFunction):
    command = "substr"
    aggregator = django.db.models.functions.Substr

    def process_arguments(self, argument_string):
        # This will ensure we have array of exactly 3 items.
        #   If there are 2, the appended None will be incldued - this is a substring of starting pos to the end.
        #   If there are 3, this is a substring of starting pos to the end position.
        field, start_pos, end_pos = (argument_string.split(',') + [None])[0:3]
        return [field, start_pos, end_pos], {}



@register_aggregator
class Concat(InterrogatorFunction):
    command = "concat"
    aggregator = django.db.models.functions.Concat

    def process_arguments(self, argument_string):
        fields = []
        for f in argument_string.split(','):
            if f.startswith(('"', "'")):
                # its a string!
                fields.append(Value(f.strip('"').strip("'")))
            else:
                fields.append(f)
        return fields, {}



@register_aggregator
class SumIf(InterrogatorFunction):
    command = "sumif"
    aggregator = SumIf

    def process_arguments(self, argument_string):
        field = argument_string
        try:
            field, cond = field.split(',', 1)
        except:
            raise di_exceptions.InvalidAnnotationError("SUMIF must have a condition")
        field = normalise_math(field)
        conditions = {}
        for condition in cond.split(','):
            condition_key, condition_val = condition.split('=', 1)
            conditions[normalise_field(condition_key)] = normalise_field(condition_val)
        return [field], conditions



@register_aggregator
class ComplexLookup(InterrogatorFunction):
    command = "lookup"
    aggregator = ComplexLookup

    def process_arguments(self, argument_string):
        try:
            field, cond, value = argument_string.split(',', 2)
        except:
            raise di_exceptions.InvalidAnnotationError("Not enough arguments - must be 3")
        return [field, cond, value], {}
