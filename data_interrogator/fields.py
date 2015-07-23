from django.forms.fields import MultiValueField, CharField
from django.forms.widgets import TextInput, MultiWidget
from django.utils.html import conditional_escape, format_html
from django.utils.safestring import mark_safe

DELIMITER="||"

class MultipleCharInput(MultiWidget):
    class Media:
        js = ('multicharfield/multicharfield.js',)
        css = {'all': ('multicharfield/multicharfield.css',)}

    def __init__(self, extra=1, add_text="Add field", remove_text="x",remove_title="remove field", attrs={}, *args, **kwargs):
        self.extra = int(extra)
        self.add_text = add_text
        self.remove_text = remove_text
        self.remove_title = remove_title
        widgets = self.get_widgets(self.extra,attrs)
        super(MultipleCharInput,self).__init__(widgets, attrs=None,*args, **kwargs)

    def get_widgets(self,number,attrs):
        self.extra = int(number)
        widgets = [RemovableTextInput(remove_text=self.remove_text,remove_title=self.remove_title,attrs=attrs) for i in range(number)]
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

        html = super(MultipleCharInput,self).render(name, value, attrs)

        return format_html(''.join([
            "<div class='multicharfield'>",
            "<span>"+html+"</span>",
            "<span style='display:none;'>",
            RemovableTextInput(remove_text=self.remove_text,remove_title=self.remove_title,attrs=attrs).render(name=name,value=""),
            "</span>",
            "<input type='button' value='%s' onclick='addColumn(this.parentElement);return false' />"%self.add_text,
            "</div>"
            ]))

    def value_from_datadict(self, data, files, name):
        values = [v for v in data.getlist(name) if v != ""]
        return values

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

class RemovableTextInput(TextInput):
    def __init__(self, extra=1, remove_text="x",remove_title="remove", *args, **kwargs):
        self.remove_text = remove_text
        self.remove_title = remove_title
        super(RemovableTextInput,self).__init__(*args, **kwargs)

    def render(self, name, value, attrs={}):
        name = name.rsplit('_',1)[0]
        html = super(RemovableTextInput,self).render(name, value, attrs=attrs)
        return format_html(
            "<div class='multichar-field-group'>"+html+"<input type='button' value='%s' title='%s' onclick='removeColumn(this);return false' /></div>"%(self.remove_text,self.remove_title)
            )
        
