import sqlparse
from datetime import datetime
from django.db import connection
from django.db.models import Case, Lookup, Sum, Transform, Q, When
from django.db.models.fields import DateField, DateTimeField, Field
# from django.db.models.functions.datetime import TruncBase


@Field.register_lookup
class NotEqual(Lookup):
    lookup_name = 'ne'

    def as_sql(self, compiler, connection):
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        params = lhs_params + rhs_params
        return '%s != %s' % (lhs, rhs), params

# @DateField.register_lookup
# @DateTimeField.register_lookup
# class TruncQuarter(Transform):
#     function = 'DATE_TRUNC'
#     template = "%(function)s('quarter', %(expressions)s)"
#     lookup_name = 'quarter'

#     def __init__(self, expression, output_field=DateTimeField(), **extra):
#         super().__init__(expression, output_field=output_field, **extra)

#     def resolve_expression(self, query=None, allow_joins=True, reuse=None, summarize=False, for_save=False):
#         copy = super().resolve_expression(query, allow_joins, reuse, summarize, for_save)

#         input_field = copy.lhs.output_field
#         if not isinstance(input_field, (DateField, DateTimeField)):
#             raise ValueError('Input expression must be either DateField or DateTimeField, not %r', input_field.name)

#         output_field = copy.output_field
#         if not isinstance(output_field, (DateField, DateTimeField)):
#             raise ValueError('output_field must be either DateField or DateTimeField, not %r', output_field.name)
#         return copy

#     def convert_value(self, value, expression, connection, context):
#         if isinstance(value, datetime) and type(self.output_field) == DateField:
#             # we asked for a date but got a datetime
#             value = value.date()
#         return value

#     def as_sqlite(self, compiler, connection):
#         raise NotImplementedError('sqlite does not support truncating to Quarter.')


# @DateField.register_lookup
# @DateTimeField.register_lookup
# class TruncQtr(TruncBase):
#     kind = 'quarter'
#     lookup_name = 'qtr'


# analyticsql = """
# SELECT
#     quarter,
#     revenue,
#     round((
#         revenue / LAG(revenue) over (ORDER BY quarter) - 1
#     ) * 100, 2) || '%' rgrowth
# FROM (
#     SELECT
#         DATE_TRUNC('quarter', s.sale_date) quarter,
#         SUM(s.sale_price)                  revenue
#     FROM shop_sale    s
#     JOIN shop_product p ON s.product_id = p.id
#     GROUP BY DATE_TRUNC('quarter', s.sale_date)
#     ORDER BY quarter
# ) quarterly_revenue
# """


# def qtr_over_qtr_revenue():
#     cursor = connection.cursor()
#     cursor.execute(analyticsql)
#     columns = [column[0] for column in cursor.description]
#     for row in cursor:
#         yield dict(zip(columns, row))


# def sql(queryset):
#     return sqlparse.format(str(queryset.query), reindent=True)
