from django import template
from django.template import Context
from django.template.loader import get_template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def lookup(dictionary, key):
    value = dictionary[key]
    return value


@register.simple_tag(takes_context=True)
def lineup(context, base_models=None):
    return get_template("data_interrogator/lineup.html").render(context)


@register.simple_tag(takes_context=True)
def interrogation_room(context):
    return get_template("data_interrogator/table_display.html").render(context)


@register.simple_tag
def clean_column_name(column_name):
    if '___' in column_name:
        # we have an aggregation of some kind.
        column_name = column_name.replace('___', '(<wbr>') + ')'
    column_name = column_name.replace('__', '.').replace('_', ' ')
    column_name = column_name.replace(".", '<wbr>.')
    return mark_safe(column_name)


@register.simple_tag(takes_context=True)
def custom_cell_display(context, data, field):
    base_model = context.get('base_model', {})
    extra_context = context
    extra_context['data'] = data
    template = base_model.get("custom_cell_displays", {}).get(field, {}).get("template", None)
    if template:
        return get_template(template).render(extra_context)
    else:
        return data[field]


@register.filter
def has_sorter(base_model, field):
    sorter = base_model.get("custom_cell_displays", {}).get(field, {}).get("sort", None)
    if sorter:
        return True
    else:
        return False


@register.simple_tag(takes_context=True)
def sort_value(context, data, field):
    base_model = context.get('base_model', {})
    sorter = base_model.get("custom_cell_displays", {}).get(field, {}).get("sort", None)
    if sorter:
        return 'data-value="%s"' % data[sorter]
    else:
        return ''


@register.simple_tag
def static_interrogation_room(table):
    from data_interrogator.views import interrogate

    filters = [f.filter_definition for f in table.filters.all()]
    columns = [c.column_definition for c in table.columns.all()]
    headers = [(c.column_definition, c.header_text or c.column_definition) for c in table.columns.all()]
    orderby = [f.ordering for f in table.order.all()]
    base_model = table.base_model
    data = interrogate(base_model, columns=columns, headers=headers, filters=filters, order_by=orderby,
                       limit=table.limit)
    data.pop('count')
    return get_template("data_interrogator/table_display.html").render(Context(data))
