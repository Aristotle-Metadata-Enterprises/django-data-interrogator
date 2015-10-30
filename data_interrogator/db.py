from django.db.models import Aggregate, CharField
from django.db.models import Lookup
from django.db.models.fields import Field#, RelatedField
from django.db.models.fields.related import RelatedField,ForeignObject,ManyToManyField
from django.db.models.expressions import Func

# This is different to the built in Django Concat command, as that concats columns in a row
# This concats one column from a selection of rows together.
class Concat(Aggregate):
    # supports COUNT(distinct field)
    function = 'GROUP_CONCAT'
    template = '%(function)s(%(distinct)s%(expressions)s)'
    
    def __init__(self, expression, distinct=False, **extra):
        super(Concat, self).__init__(
            expression,
            distinct='DISTINCT ' if distinct else '',
            output_field=CharField(),
            **extra)

# SQLite function to force a date time subtraction to come out correctly.
# This just returns the expression on every other database backend.

class ForceDate(Func):
    function = ''
    template = "%(expressions)s"
    def __init__(self, expression, **extra):
        self.__expression = expression
        super(ForceDate, self).__init__(expression, **extra)

    def as_sqlite(self, compiler, connection):
        self.function = 'julianday'
        self.template = 'coalesce(%(function)s(%(expressions)s),julianday())*24*60*60*1000*1000' # Convert julian day to microseconds as used by Django DurationField
        return super(ForceDate, self).as_sql(compiler, connection)

class NotEqual(Lookup):
    lookup_name = 'ne'

    def as_sql(self, qn, connection):
        lhs, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        params = lhs_params + rhs_params
        return '%s <> %s' % (lhs, rhs), params
Field.register_lookup(NotEqual)
RelatedField.register_lookup(NotEqual)
ForeignObject.register_lookup(NotEqual)
ManyToManyField.register_lookup(NotEqual)
