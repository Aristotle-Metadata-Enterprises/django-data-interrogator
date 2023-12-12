from django.db.models import Aggregate, CharField, TextField
from django.db.models import Case, Lookup, Sum, Q, When, Value
from django.db.models.functions import Coalesce, Cast
from django.db.models.expressions import Func
from django.db.models.fields import DecimalField, Field, FloatField  # , RelatedField
from django.db.models.fields.related import RelatedField, ForeignObject, ManyToManyField


from django.db.models.functions import Lower

# This is different to the built in Django Concat command, as that concats columns in a row
# This concatenates one column from a selection of rows together.
class GroupConcat(Aggregate):
    # supports COUNT(distinct field)
    function = 'GROUP_CONCAT'
    template = '%(function)s(%(distinct)s%(expressions)s)'

    def __init__(self, expression, distinct=False, output_field=CharField(), **extra):
        super().__init__(
            expression,
            distinct='DISTINCT ' if distinct else '',
            output_field=output_field,
            **extra)

    def as_microsoft(self, compiler, connection):
        self.function = 'max'  # MSSQL doesn't support GROUP_CONCAT yet.
        self.template = '%(function)s(%(expressions)s)'
        return super().as_sql(compiler, connection)

    def as_postgresql(self, compiler, connection):
        self.function = "STRING_AGG"
        self.template = "%(function)s(%(distinct)s%(expressions)s, ',')"
        return super().as_sql(compiler, connection)


def ComplexLookup(lookup_field, condition, lookup_value, output_field=TextField()):
    expression = Coalesce(
        GroupConcat(
            Cast(
                Case(
                    When(**{lookup_field: condition, 'then': lookup_value}),
                    default=Value(None),
                    output_field=output_field
                ),
                output_field=TextField()
            )
        ),
        Value("")
    )
    return expression


class SumIf(Sum):
    """
    Executes the equivalent of
        Python: `Sum(Case(When(condition, then=field), default=None))`
        SQL: `SUM(CASE WHEN condition THEN field ELSE NULL END)`
    """

    def __init__(self, field, condition=None, output_field=DecimalField(), **lookups):
        # Default output field is DecimalField - to decimal precision as a safe default.
        if lookups and condition is None:
            condition = Q(**lookups)
        case = Case(
            When(
                condition, then=field
                ), 
                default=0,
                output_field=output_field
                )
        super(SumIf, self).__init__(case)


class ForceDate(Func):
    """
    SQLite specific function to force a date time subtraction to come out correctly.
    This just returns the expression on every other database backend
    """
    function = ''
    template = "%(expressions)s"
    arity = 1

    def __init__(self, expression, **extra):
        self.__expression = expression
        super(ForceDate, self).__init__(expression, **extra)

    def as_sqlite(self, compiler, connection):
        self.function = ''
        self.template = 'coalesce(julianday(%(expressions)s),julianday())*24*60*60*1000*1000'  # Convert julian day to microseconds as used by Django DurationField
        return super(ForceDate, self).as_sql(compiler, connection)

    def as_microsoft(self, compiler, connection):
        self.function = ''
        self.template = 'coalesce(%(expressions)s,GETDATE())'  # *24*60*60*1000*1000' # Convert julian day to microseconds as used by Django DurationField
        return super(ForceDate, self).as_sql(compiler, connection)


class DateDiff(Func):
    function = ''
    template = '%(expressions)s'
    arg_joiner = ' - '
    arity = 2

    def __init__(self, start, end):
        super(DateDiff, self).__init__(start, end)

    def as_microsoft(self, compiler, connection):
        self.template = 'cast(DateDiff(day,%(expressions)s) as float)* -1 *24*60*60*1000.0*1000.0'  # Convert to microseconds as used by Django DurationField'
        self.arg_joiner = ', '
        return super(DateDiff, self).as_sql(compiler, connection)

    def as_sql(self, compiler, connection, function=None, template=None):
        if connection.vendor == 'microsoft':
            return self.as_microsoft(compiler, connection)
        return super(DateDiff, self).as_sql(compiler, connection)


class NotEqual(Lookup):
    lookup_name = 'ne'

    def as_sql(self, qn, connection):
        lhs, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        params = lhs_params + rhs_params
        return '%s != %s' % (lhs, rhs), params


Field.register_lookup(NotEqual)
RelatedField.register_lookup(NotEqual)
ForeignObject.register_lookup(NotEqual)
ManyToManyField.register_lookup(NotEqual)
