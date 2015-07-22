from django.forms.fields import MultiValueField, CharField
from django.forms.widgets import TextInput, MultiWidget
from django.utils.html import conditional_escape, format_html
from django.utils.safestring import mark_safe

DELIMITER="||"

class MultipleCharInput(MultiWidget):
    class Media:
        js = ('multicharfield/multicharfield.js',)

    def __init__(self, extra=1, add_text="Add column", remove_text="-", attrs={}, *args, **kwargs):
        if 'data' in kwargs.keys():
            print("here is data",kwargs.get('data'))
            extra = len(kwargs.get('data'))
        self.extra = int(extra)
        self.add_text = add_text
        self.remove_text = remove_text
        
        widgets = []
        for i in range(self.extra):
            widgets.append(RemovableTextInput(attrs=attrs))
        widgets = tuple(widgets)
        super(MultipleCharInput,self).__init__(widgets, attrs=None,*args, **kwargs)

    def decompress(self, value):
        if value:
            values = value.split(DELIMITER)
            values = [v for v in values if v != ""]
            return values
        return ['']*self.extra

    def render(self, name, value, attrs=None):
        html = super(MultipleCharInput,self).render(name, value, attrs)

        return format_html(
            "<div><span>"+html+"""</span>
            <span style="display:none;">"""+RemovableTextInput().render(name=name,value="")+"""</span>
            <input type='button' value='%s' onclick='addColumn(this.parentElement);return false' /></div>"""%self.add_text
            )

    def value_from_datadict(self, data, files, name):
        return data.getlist(name)

class MultipleCharField(MultiValueField):
    widget = MultipleCharInput
    def __init__(self, extra=1, *args, **kwargs):
        self.extra = int(extra)
        fields = tuple(
                [CharField(required=False) for w in range(self.extra)]
            )
        super(MultipleCharField,self).__init__(fields, *args, **kwargs)
        self.widget = MultipleCharInput(extra=extra)

    def compress(self, values):
        if values:
            values = [v for v in values if v != ""]
            return DELIMITER.join(values)
        return ''

    def clean(self, value):
        return value

class RemovableTextInput(TextInput):
    def render(self, name, value, attrs={},remove_text="-"):
        name = name.rsplit('_',1)[0]
        html = super(RemovableTextInput,self).render(name, value, attrs=attrs)
        return format_html(
            "<div>"+html+"<input type='button' value='%s' onclick='removeColumn(this);return false' /></div>"%remove_text
            )
        
