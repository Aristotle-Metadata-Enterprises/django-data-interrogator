from django import template
from django.core.urlresolvers import reverse, resolve
from django.template.loader import get_template

register = template.Library()

@register.simple_tag
def lookup(dictionary,key):
    value = dictionary[key]
    return value

@register.simple_tag(takes_context=True)
def lineup(context,suspects=None):
    return get_template("data_interrogator/lineup.html").render(context)


@register.simple_tag(takes_context=True)
def interrogation_room(context):
    return get_template("data_interrogator/interrogation_room.html").render(context)

