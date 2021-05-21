import re
from datetime import timedelta
from enum import Enum
from typing import Union, Tuple, List

from django.apps import apps
from django.core import exceptions
from django.conf import settings
from django.db.models import F, Count, Min, Max, Sum, Value, Avg, ExpressionWrapper, DurationField, FloatField, Model
from django.db.models import functions as func

from data_interrogator import exceptions as di_exceptions
from data_interrogator.db import GroupConcat, DateDiff, ForceDate, SumIf

# Utility functions
math_infix_symbols = {
    '-': lambda a, b: a - b,
    '+': lambda a, b: a + b,
    '/': lambda a, b: a / b,
    '*': lambda a, b: a * b,
}

# Large unit multipliers to filter across
BIG_MULTIPLIERS = {
    'day': 1,
    'week': 7,
    'fortnight': 14,
    'month': 30,  # close enough
    'year': 365,
    'decade': 10 * 365,
}
# Small unit multipliers to filter across
LITTLE_MULTIPLIERS = {
    'second': 1,
    'minute': 60,
    'hour': 60 * 60,
    'microfortnight': 1.2,  # sure why not?
}


def get_base_model(app_label: str, model: str) -> Model:
    """Get the actual base model, from the """
    return apps.get_model(app_label.lower(), model.lower())

# might need a get_model_queryset

def normalise_field(text) -> str:
    """Replace the UI access with the backend Django access"""
    return text.strip().replace('(', '::').replace(')', '').replace(".", "__")


def normalise_math(expression):
    """Normalise math from UI """
    if not any(s in expression for s in math_infix_symbols.keys()):
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


def clean_filter(text: str) -> Union[str, Tuple[str, str, str]]:
    """Return the (cleaned) filter for replacement"""
    maps = [('<>', 'ne'), ('<=', 'lte'), ('<', 'lt'), ('>=', 'gte'), ('>', 'gt'), ('=', '')]
    for interrogator_filter, django_filter in maps:
        candidate = text.split(interrogator_filter)
        if len(candidate) == 2:
            if interrogator_filter is "=":
                return candidate[0], django_filter, candidate[1]
            return candidate[0], '__%s' % django_filter, candidate[1]
    return text


class Allowable(Enum):
    ALL_APPS = 1
    ALL_MODELS = 1
    ALL_FIELDS = 3


class Interrogator:
    available_aggregations = {
        "min": Min,
        "max": Max,
        "sum": Sum,
        'avg': Avg,
        "count": Count,
        "substr": func.Substr,
        "group": GroupConcat,
        "concat": func.Concat,
        "sumif": SumIf,
    }
    errors = []
    report_models = Allowable.ALL_MODELS

    # both of these are lists of either:
    #   ('app_label',)
    #   ('app_label', 'model_name')
    #   Not this yet: ('app_label', 'model_name', ['list of field names'])
    allowed = Allowable.ALL_MODELS
    excluded = []
    # model_queryset = None


    def __init__(self, report_models=None, allowed=None, excluded=None):
        if report_models is not None:
            self.report_models = report_models
        if allowed is not None:
            self.allowed = allowed
        if excluded is not None:
            self.excluded = excluded
        
        # this could be a good place to add the qs

        # Clean up rules if they aren't lower cased.
        fixed_excluded = []
        for rule in self.excluded:
            if len(rule) == 1:
                rule = (rule[0].lower(),)
            if len(rule) == 2:
                rule = (rule[0].lower(), rule[1].lower())
            if len(rule) == 3:
                rule = (rule[0].lower(), rule[1].lower(), rule[2])
            fixed_excluded.append(rule)
        self.excluded = fixed_excluded

        if self.allowed != Allowable.ALL_MODELS:
            self.allowed_apps = [
                i[0] for i in allowed
                if type(i) is str or type(i) is tuple and len(i) == 1
            ]

        if self.allowed != Allowable.ALL_APPS:
            self.allowed_models = [
                i[:2] for i in allowed
                if type(i) is tuple and len(i) == 2
            ]
        else:
            self.allowed_models = Allowable.ALL_MODELS

    def is_hidden_field(self, field) -> bool:
        """Returns whether a field begins with an underscore and so is hidden"""
        if hasattr(settings, 'INTERROGATOR_INCLUDED_HIDDEN_FIELDS') and field.name in settings.INTERROGATOR_INCLUDED_HIDDEN_FIELDS:
            return False

        return field.name.startswith('_')

    # def get_model_queryset(self, qs_restriction_function=None):
    def get_model_queryset(self):
        return self.base_model.objects.all()
        # qs = self.base_model.objects.all()

        # if qs_restriction_function is None:
        #     return qs
        
        # return qs_restriction_function(qs)
    # get model_queryset from self if its there
    # def get_model_queryset(self):
    #     if self.model_queryset is None:
    #         return self.base_model.objects.all()

    #     return self.model_queryset()

    def process_annotation_concat(self, column):
        pass

    def process_annotation(self, column):
        pass

    def is_allowed_model(self, model):
        pass

    def verify_column(self, column):
        model = self.base_model
        args = column.split('__')
        for a in args:
            model = [f for f in model._meta.get_fields() if f.name == a][0].related_model

    def get_field_by_name(self, model, field_name):
        return model._meta.get_field(field_name)

    def is_excluded_field(self, field_path, base_model=None) -> bool:
        """
        Accepts dundered path from model
        TODO: currently we're not doing per field permission checks, add this later
        """
        return False

    def is_excluded_model(self, model_class) -> bool:
        """Returns whether a model should be excluded"""
        app_label = model_class._meta.app_label
        model_name = model_class._meta.model_name

        # Special case to include content type
        if model_name == 'contenttype':
            return False

        if app_label in self.excluded or (app_label, model_name) in self.excluded:
            return True

        if self.allowed == Allowable.ALL_MODELS:
            return False

        excluded = not (app_label in self.allowed or ((app_label, model_name) in self.allowed))
        return excluded

    def has_forbidden_join(self, column, base_model=None) -> bool:
        """Return whether a forbidden join exists in the query"""
        checking_model = base_model or self.base_model

        joins = column.split('__')
        for _, relation in enumerate(joins):
            if checking_model:
                try:
                    attr = self.get_field_by_name(checking_model, relation)
                    if attr.related_model:
                        if self.is_excluded_model(attr.related_model):
                            # Despite the join/field being named differently, this column is forbidden!
                            return True
                    checking_model = attr.related_model
                except exceptions.FieldDoesNotExist:
                    pass

        return False

    def get_base_annotations(self):
        return {}

    def get_annotation(self, column):
        agg, field = column.split('::', 1)
        if agg == 'sumif':
            try:
                field, cond = field.split(',', 1)
            except:
                raise di_exceptions.InvalidAnnotationError("SUMIF must have a condition")
            field = normalise_math(field)
            conditions = {}
            for condition in cond.split(','):
                condition_key, condition_val = condition.split('=', 1)
                conditions[normalise_field(condition_key)] = normalise_field(condition_val)
            annotation = self.available_aggregations[agg](field=field, **conditions)
        elif agg == 'join':
            fields = []
            for f in field.split(','):
                if f.startswith(('"', "'")):
                    # its a string!
                    fields.append(Value(f.strip('"').strip("'")))
                else:
                    fields.append(f)
            annotation = self.available_aggregations[agg](*fields)
        elif agg == "substr":
            field, i, j = (field.split(',') + [None])[0:3]
            annotation = self.available_aggregations[agg](field, i, j)
        else:
            field = normalise_math(field)
            annotation = self.available_aggregations[agg](field, distinct=False)
        return annotation

    def validate_report_model(self, base_model):
        app_label, model = base_model.split(':', 1)
        base_model = apps.get_model(app_label.lower(), model.lower())

        extra_data = {}

        if (app_label, model) in self.excluded or base_model in self.excluded:
            self.base_model = None
            raise di_exceptions.ModelNotAllowedException(model=base_model)

        if self.report_models == Allowable.ALL_MODELS:
            return base_model, extra_data

        for opts in self.report_models:
            if opts[:2] == (app_label, model):
                return base_model, extra_data

        self.base_model = None
        raise di_exceptions.ModelNotAllowedException()

    def check_for_forbidden_column(self, column) -> List[str]:
        """Check if column is forbidden for whatever reason, and return the value of it"""
        errors: List[str] = []

        # Check if the column has permission
        if self.has_forbidden_join(column):
            errors.append(
                "Joining tables with the column [{}] is forbidden, this column is removed from the output.".format(
                    column))
        # Check aggregation includes a forbidden column
        if '::' in column:
            check_col = column.split('::', 1)[-1]
            if self.has_forbidden_join(check_col):
                errors.append(
                    "Aggregating tables using the column [{}] is forbidden, this column is removed from the output.".format(
                        column))
        return errors

    def generate_filters(self, filters, annotations, expression_columns):
        errors = []
        annotation_filters = {}
        _filters = {}
        excludes = {}
        filters_all = {}

        for index, expression in enumerate(filters):
            field, exp, val = clean_filter(normalise_field(expression))

            if self.has_forbidden_join(field):
                errors.append(
                    f"Filtering with the column [{field}] is forbidden, this filter is removed from the output."
                )
                continue

            key = '%s%s' % (field.strip(), exp)
            val = val.strip()

            if val.startswith('~'):
                val = F(val[1:])
            elif key.endswith('date'):
                val = (val + '-01-01')[:10]  # If we are filtering by a date, make sure its 'date-like'
            elif key.endswith('__isnull'):
                if val == 'False' or val == '0':
                    val = False
                else:
                    val = bool(val)

            if '::' in field:
                # We've got an annotated filter
                agg, f = field.split('::', 1)
                field = 'f%s%s' % (index, field)
                key = 'f%s%s' % (index, key)
                annotations[field] = self.available_aggregations[agg](f, distinct=True)
                annotation_filters[key] = val
            elif key in annotations.keys():
                annotation_filters[key] = val
            elif key.split('__')[0] in expression_columns:
                k = key.split('__')[0]
                if 'date' in k and key.endswith('date') or 'date' in str(annotations[k]):
                    val, period = (val.rsplit(' ', 1) + ['days'])[0:2]
                    # this line is complicated, just in case there is no period or space
                    period = period.rstrip('s')  # remove plurals

                    kwargs = {}
                    if BIG_MULTIPLIERS.get(period, None):
                        kwargs['days'] = int(val) * BIG_MULTIPLIERS[period]
                    elif LITTLE_MULTIPLIERS.get(period, None):
                        kwargs['seconds'] = int(val) * LITTLE_MULTIPLIERS[period]

                    annotation_filters[key] = timedelta(**kwargs)

                else:
                    annotation_filters[key] = val

            elif key.endswith('__all'):
                key = key.rstrip('_all')
                val = [v for v in val.split(',')]
                filters_all[key] = val
            else:
                exclude = key.endswith('!')
                if exclude:
                    key = key[:-1]
                if key.endswith('__in'):
                    val = [v for v in val.split(',')]
                if exclude:
                    excludes[key] = val
                else:
                    _filters[key] = val

        return filters_all, _filters,  annotations, expression_columns, excludes

    def generate_queryset(self, base_model, model_queryset,
    columns=None, filters=None, order_by=None, limit=None, offset=0):
        errors = []
        annotation_filters = {}

        self.base_model, base_model_data = self.validate_report_model(base_model)
        wrap_sheets = base_model_data.get('wrap_sheets', {})

        annotations = self.get_base_annotations()
        expression_columns = []
        output_columns = []
        query_columns = []
        
        
        # Generate filters
        for column in columns:
            var_name = None
            if column == "":
                # If the field is empty, don't do anything
                continue

            if ':=' in column:
                var_name, column = column.split(':=', 1)

            # Map names in UI to django functions
            column = normalise_field(column)

            if var_name is None:
                var_name = column

            # Check if the column has permission
            column_permission_errors = self.check_for_forbidden_column(column)
            if column_permission_errors:
                # If there are permission errors, add to error list, and don't continue
                errors.extend(column_permission_errors)
                continue

            # Build columns
            if column.startswith(tuple([a + '::' for a in self.available_aggregations.keys()])):
                annotations[var_name] = self.get_annotation(column)

            elif any(s in column for s in math_infix_symbols.keys()):
                annotations[var_name] = self.normalise_math(column)
                expression_columns.append(var_name)
            else:
                if column in wrap_sheets.keys():
                    cols = wrap_sheets.get(column).get('columns', [])
                    query_columns = query_columns + cols
                else:
                    if var_name == column:
                        query_columns.append(var_name)
                    else:
                        annotations[var_name] = F(column)
            output_columns.append(var_name)

#       rows = self.get_model_queryset()
        rows = model_queryset

        # Generate filters
        filters_all, _filters, annotations, expression_columns, excludes = self.generate_filters(
            filters=filters,
            annotations=annotations,
            expression_columns=expression_columns
        )

    #   filters the rows which are supplied
        rows = rows.filter(**_filters)
        for key, val in filters_all.items():
            for v in val:
                rows = rows.filter(**{key: v})
        rows = rows.exclude(**excludes)
        rows = rows.values(*query_columns)

        if annotations:
            rows = rows.annotate(**annotations)
            rows = rows.filter(**annotation_filters)
        if order_by:
            ordering = map(normalise_field, order_by)
            rows = rows.order_by(*ordering)

        if limit:
            lim = abs(int(limit))
            rows = rows[offset:lim]

        return rows, errors, output_columns, base_model_data

    def interrogate(self, base_model, columns=None, filters=None, order_by=None, limit=None, offset=0, model_queryset=None):
        if order_by is None: order_by = []
        if filters is None: filters = []
        if columns is None: columns = []

        errors = []
        base_model_data = {}
        output_columns = []
        count = 0
        rows = []

        # gets model supplied - if not supplied, gets model the original way
        if not model_queryset:
            model_queryset = self.get_model_queryset()

        try:
            rows, errors, output_columns, base_model_data = self.generate_queryset(
                base_model, 
                columns,
                filters,
                order_by,
                limit,
                offset, 
                model_queryset,
            )
            if errors:
                rows = rows.none()
            rows = list(rows)  # Force a database hit to check the in database state
            count = len(rows)

        except di_exceptions.InvalidAnnotationError as e:
            errors.append(e)

        except ValueError as e:
            rows = []
            if limit is None:
                errors.append("Limit must be a number")
            elif limit < 1:
                errors.append("Limit must be a number greater than zero")
            else:
                errors.append("Something went wrong - %s" % e)

        except IndexError as e:
            rows = []
            errors.append("No rows returned for your query, try broadening your search.")

        except exceptions.FieldError as e:
            rows = []
            if str(e).startswith('Cannot resolve keyword'):
                field = str(e).split("'")[1]
                errors.append("The requested field '%s' was not found in the database." % field)
            else:
                errors.append("An error was found with your query:\n%s" % e)
        except Exception as e:
            rows = []
            errors.append("Something went wrong - %s" % e)

        return {
            'rows': rows, 'count': count, 'columns': output_columns, 'errors': errors,
            'base_model': base_model_data
        }
    



class PivotInterrogator(Interrogator):
    def __init__(self, aggregators, **kwargs):
        super().__init__(**kwargs)
        self.aggregators = aggregators

    def get_base_annotations(self):
        aggs = {
            x: self.get_annotation(normalise_field(x)) for x in self.aggregators
            if not self.has_forbidden_join(column=x)
        }
        aggs.update({"cell": Count(1)})
        return aggs

    def pivot(self):
        # Only accept the first two valid columns
        self.columns = [normalise_field(c) for c in self.columns if not self.has_forbidden_join(column=c)][:2]

        data = self.interrogate()
        out_rows = {}

        col_head = self.base_model.objects.values(self.columns[0]).order_by(self.columns[0]).distinct()

        x, y = self.columns[:2]

        from collections import OrderedDict
        default = OrderedDict([(c[x], {'count': 0}) for c in col_head])
        for r in data['rows']:
            this_row = out_rows.get(r[y], default.copy())
            this_row[r[x]] = {'count': r['cell'],
                              'aggs': [(k, v) for k, v in r.items() if k not in ['cell', x, y]]
                              }
            out_rows[r[y]] = this_row

        return {
            'rows': out_rows, 'col_head': col_head, 'errors': data['errors'],
            'base_model': data['base_model'], 'headers': data['headers']
        }

