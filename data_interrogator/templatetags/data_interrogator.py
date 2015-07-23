from django import template
from django.core.urlresolvers import reverse, resolve
from django.template import Context
from django.template.loader import get_template

register = template.Library()

@register.filter
def lookup(dictionary,key):
    value = dictionary[key]
    return value

@register.simple_tag(takes_context=True)
def lineup(context,suspects=None):
    return get_template("data_interrogator/lineup.html").render(context)


@register.simple_tag(takes_context=True)
def interrogation_room(context):
    return get_template("data_interrogator/interrogation_room.html").render(context)

@register.simple_tag
def clean_column_name(column_name):
    if '___' in column_name:
        #we have an aggregation of some kind.
        column_name = column_name.replace('___','(')+')'
    column_name = column_name.replace('__','.').replace('_',' ')
    return column_name

@register.simple_tag(takes_context=True)
def wrap_sheet(context,data,field):
    suspect = context.get('suspect',{})
    extra_context = context
    extra_context['data'] = data
    template = suspect.get("wrap_sheets",{}).get(field,{}).get("template",None)
    if template:
        return get_template(template).render(extra_context)
    else:
        return data[field]
