from datetime import timedelta
from typing import Union, Tuple, List

from django.apps import apps
from django.core import exceptions
from django.conf import settings
# from django.db.models import Count, Min, Max, Sum, Value, Avg
from django.db.models import F, Model, JSONField
from django.db.models import functions as func

from data_interrogator import exceptions as di_exceptions
from data_interrogator.aggregators import aggregate_register
from data_interrogator.utils import normalise_field, normalise_math, Allowable, is_math_expression



try:
    from garnett.expressions import L
    from garnett.fields import TranslatedField
    GARNETT_ENABLED = True
except:
    GARNETT_ENABLED = False


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

LEXP = "l_exp____"


def get_base_model(app_label: str, model: str) -> Model:
    """Get the actual base model, from the """
    return apps.get_model(app_label.lower(), model.lower())




def clean_lexp_key(key):
    if key.startswith(LEXP):
        return key[len(LEXP):]
    return key



def clean_filter(text: str) -> Union[str, Tuple[str, str, str]]:
    """Return the (cleaned) filter for replacement"""
    # The order of 'not in' and 'in' operators is important
    maps = [
        ('<>', 'ne'), ('<=', 'lte'), ('<', 'lt'), ('>=', 'gte'), ('>', 'gt'), ('=', ''),
        ('&contains', 'contains'), ('&icontains', 'icontains'),
        ('not in', 'in!'), ('in', 'in')
    ]
    for interrogator_filter, django_filter in maps:
        candidate = text.split(interrogator_filter)
        if len(candidate) == 2:
            if interrogator_filter == "=":
                return candidate[0], django_filter, candidate[1]
            return candidate[0], '__%s' % django_filter, candidate[1]
    return text



class Interrogator:
    available_aggregations = aggregate_register
    errors = []
    report_models = Allowable.ALL_MODELS

    # both of these are lists of either:
    #   ('app_label',)
    #   ('app_label', 'model_name')
    #   Not this yet: ('app_label', 'model_name', ['list of field names'])
    allowed = Allowable.ALL_MODELS
    excluded = []

    def __init__(self, report_models=None, allowed=None, excluded=None):
        if report_models is not None:
            self.report_models = report_models
        if allowed is not None:
            self.allowed = allowed
        if excluded is not None:
            self.excluded = excluded

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

    def get_model_queryset(self):
        return self.base_model.objects.all()

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
            if model:
                # If there is no model, its not a foreign key, so its safe as its either
                # a transform or a key JSON lookup.
                model = [f for f in model._meta.get_fields() if f.name == a][0].related_model

    def get_field_by_name(self, model, field_name):
        return model._meta.get_field(field_name)

    def is_excluded_field(self, model, field) -> bool:
        """
        Accepts model and field object
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

    def has_forbidden_field(self, column) -> bool:
        """Return whether a forbidden field exists in the query"""
        checking_model = self.base_model

        joins = column.split('__')
        for _, relation in enumerate(joins):
            if checking_model:
                try:
                    field = self.get_field_by_name(checking_model, relation)
                    if isinstance(field, JSONField):
                        # This is safe as you can't foreign key out of a JSONField
                        return False
                    if field.related_model:
                        if self.is_excluded_model(field.related_model):
                            # Despite the join/field being named differently, this column is forbidden!
                            return True
                    if self.is_excluded_field(checking_model, field):
                        # Despite the join/field being named differently, this column is forbidden!
                        return True
                    checking_model = field.related_model
                except exceptions.FieldDoesNotExist:
                    pass

        return False

    def is_translatable(self, column) -> bool:
        """Return whether a forbidden field exists in the query"""
        if not GARNETT_ENABLED:
            return False

        checking_model = self.base_model

        joins = list(enumerate(column.split('__')))
        for i, relation in joins:
            if checking_model:
                try:
                    field = self.get_field_by_name(checking_model, relation)
                    if isinstance(field, TranslatedField):
                        return i == len(joins) - 1
                    checking_model = field.related_model
                except exceptions.FieldDoesNotExist:
                    pass
        return False

    def get_base_annotations(self):
        return {}

    def get_annotation(self, column):
        agg, argument_string = column.split('::', 1)
        return self.available_aggregations[agg]().as_django(argument_string)


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
        if self.has_forbidden_field(column):
            errors.append(
                "Joining tables with the column [{}] is forbidden, this column is removed from the output.".format(
                    column))
        # Check aggregation includes a forbidden column
        if '::' in column:
            check_col = column.split('::', 1)[-1]
            if self.has_forbidden_field(check_col):
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

            if self.has_forbidden_field(field):
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
                if val.lower() in ['false', 'f', '0']:
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

        # _filters.update(**annotation_filters)
        return filters_all, _filters,  annotation_filters, annotations, expression_columns, excludes

    def get_model_restriction(self, model):
        return {}

    def get_model_restriction_filters(self, column) -> bool:
        """Return whether a forbidden join exists in the query"""
        checking_model = self.base_model
        restriction_filters = {}

        joins = column.split('__')
        for i, relation in enumerate(joins):
            try:
                attr = self.get_field_by_name(checking_model, relation)
                if isinstance(attr, JSONField):
                    # This is safe as you can't foreign key out of a JSONField
                    break
                if attr.related_model:
                    if restriction := self.get_model_restriction(attr.related_model):
                        for k, v in restriction.items():
                            joined_rest =  "__".join(joins[:i+1]) + "__" + k
                            restriction_filters[joined_rest] = v
                checking_model = attr.related_model
            except exceptions.FieldDoesNotExist:
                pass

        return restriction_filters

    def generate_queryset(self, base_model, columns=None, filters=None, order_by=None, limit=None, offset=0):
        errors = []
        annotation_filters = {}

        self.base_model, base_model_data = self.validate_report_model(base_model)
        wrap_sheets = base_model_data.get('wrap_sheets', {})

        annotations = self.get_base_annotations()
        expression_columns = []
        output_columns = []
        query_columns = []
        query_columns_exp = {}

        model_restriction_filters = {}
        model_restriction_filters.update(self.get_model_restriction(self.base_model))

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

            elif is_math_expression(column):
                annotations[var_name] = normalise_math(column)
                expression_columns.append(var_name)
            else:
                if column in wrap_sheets.keys():
                    cols = wrap_sheets.get(column).get('columns', [])
                    query_columns = query_columns + cols
                else:
                    if var_name == column:
                        if self.is_translatable(column):
                            query_columns_exp.update({f"{LEXP}{var_name}": L(var_name)})
                        else:
                            query_columns.append(var_name)
                    else:
                        annotations[var_name] = F(column)
            model_restriction_filters.update(self.get_model_restriction_filters(column))
            output_columns.append(var_name)

        rows = self.get_model_queryset()

        # Generate filters
        filters_all, _filters, annotation_filters, annotations, expression_columns, excludes = self.generate_filters(
            filters=filters,
            annotations=annotations,
            expression_columns=expression_columns
        )

        rows = rows.filter(**_filters)

        for key, val in filters_all.items():
            for v in val:
                rows = rows.filter(**{key: v})
        rows = rows.exclude(**excludes)

        if model_restriction_filters:
            rows = rows.filter(**model_restriction_filters)
        rows = rows.values(*query_columns, **query_columns_exp)

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

    def interrogate(self, base_model, columns=None, filters=None, order_by=None, limit=None, offset=0):
        if order_by is None: order_by = []
        if filters is None: filters = []
        if columns is None: columns = []

        errors = []
        base_model_data = {}
        output_columns = []
        count = 0
        rows = []

        try:
            rows, errors, output_columns, base_model_data = self.generate_queryset(
                base_model, columns, filters, order_by, limit, offset
            )
            if errors:
                rows = rows.none()
            rows = list(rows)  # Force a database hit to check the in database state
            _rows = []
            for row in rows:
                if row not in _rows:
                    row = {
                        clean_lexp_key(k):v
                        for k, v in row.items()
                    }
                    _rows.append(row)
            rows = _rows
            count = len(rows)

        except di_exceptions.InvalidAnnotationError as e:
            errors.append(e)

        except ValueError as e:
            rows = []
            if limit and type(limit) is int and limit < 0:
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
            'base_model': base_model_data,
            # 'query': query # DEBUG Tool
        }


class PivotInterrogator(Interrogator):
    def __init__(self, aggregators, **kwargs):
        super().__init__(**kwargs)
        self.aggregators = aggregators

    def get_base_annotations(self):
        aggs = {
            x: self.get_annotation(normalise_field(x)) for x in self.aggregators
            if not self.has_forbidden_field(column=x)
        }
        aggs.update({"cell": Count(1)})
        return aggs

    def pivot(self):
        # Only accept the first two valid columns
        self.columns = [normalise_field(c) for c in self.columns if not self.has_forbidden_field(column=c)][:2]

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
