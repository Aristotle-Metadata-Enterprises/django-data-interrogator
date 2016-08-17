from django.forms.fields import MultiValueField, CharField
from django.forms.widgets import TextInput, MultiWidget
from django.template.loader import get_template
from django.template import Context
from django.utils.html import conditional_escape, format_html
from django.utils.safestring import mark_safe

DELIMITER="||"

class MultipleCharInput(MultiWidget):
    class Media:
        js = (
            '//cdnjs.cloudflare.com/ajax/libs/corejs-typeahead/0.11.1/typeahead.bundle.js',
            'data_interrogator/multicharfield.js',
        )
        css = {
            'all': (
                'multicharfield/multicharfield.css',
            )
        }

    template_multi_char = "data_interrogator/multichar.html"
    template_multi_char_field = "data_interrogator/multicharfield.html"
    
    def __init__(self, extra=1, add_text="Add field", remove_text="x", remove_title="remove field", attrs={}, *args, **kwargs):
        self.extra = int(extra)
        self.add_text = add_text
        self.remove_text = remove_text
        self.remove_title = remove_title
        self.template_multi_char = kwargs.pop('template_multi_char', self.template_multi_char)
        self.template_multi_char_field = kwargs.pop('template_multi_char', self.template_multi_char_field)
        widgets = self.get_widgets(self.extra,attrs)
        super(MultipleCharInput,self).__init__(widgets, attrs=None,*args, **kwargs)

    def get_widgets(self,number,attrs):
        self.extra = int(number)
        widgets = [TextInput(attrs=attrs) for i in range(number)]
        return widgets

    def decompress(self, value):
        if value:
            values = value.split(DELIMITER)
            values = [v for v in values if v != ""]
            return values
        return ['']*self.extra

    def render(self, name, value, attrs=None):
        if value:
            self.widgets = self.get_widgets(len(value),attrs)

        if self.is_localized:
            for widget in self.widgets:
                widget.is_localized = self.is_localized
        # value is a list of values, each corresponding to a widget
        # in self.widgets.
        if not isinstance(value, list):
            value = self.decompress(value)
        output = []
        final_attrs = self.build_attrs(attrs)
        for i, widget in enumerate(self.widgets):
            try:
                widget_value = value[i]
            except IndexError:
                widget_value = None
            html = self.render_field(name, widget_value, final_attrs)
            output.append(html)
        html = mark_safe(self.format_output(output))
        blank_widget = self.render_field(name=name)
        return mark_safe(get_template(self.template_multi_char).render(
                {'id':name,'html':html,'blank_widget':blank_widget,'add_text':self.add_text}
            ))

    def value_from_datadict(self, data, files, name):
        if type(data ) != type({}):
            values = [v for v in data.getlist(name) if v != ""]
            return values
        return []

    def render_field(self, name, widget_value=None, final_attrs={}):
        if widget_value is None:
            widget_value = ""
        attrs = " ".join(["%s='%s'"%(key,val) for key,val in final_attrs])
        return get_template(self.template_multi_char_field).render(
            {   'remove_text':self.remove_text,
                'remove_title':self.remove_title,
                'name':name,
                'value':widget_value,
                'attrs':attrs
            }
        )


class AdminMultipleCharInput(MultipleCharInput):
    template_multi_char = "data_interrogator/admin/multichar.html"
    template_multi_char_field = "data_interrogator/admin/multicharfield.html"

class MultipleCharField(MultiValueField):
    widget = MultipleCharInput
    def __init__(self, extra=1, add_text="Add field", remove_text="x",remove_title="remove field", *args, **kwargs):
        self.extra = int(extra)
        fields = tuple(
                [CharField(required=False) for w in range(self.extra)]
            )
        super(MultipleCharField,self).__init__(fields, *args, **kwargs)
        self.widget = MultipleCharInput(extra=extra, remove_text=remove_text, remove_title=remove_title, add_text=add_text)

    def compress(self, values):
        if values:
            values = [v for v in values if v != ""]
            return DELIMITER.join(values)
        return ''

    def clean(self, value):
        return value


class AdminMultipleCharField(MultipleCharField):
    widget = AdminMultipleCharInput
