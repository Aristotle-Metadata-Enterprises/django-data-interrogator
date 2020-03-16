from django import forms

class CSVMultipleCharField(forms.CharField):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.widget.attrs = {'class': 'multicharfields'}

    def compress(self, values):
        if values:
            values = [v for v in values if v != ""]
            return '||'.join(values)
        return ''

    def clean(self, value):
        if not value:
            value = ""
        return [v.strip() for v in value.split("||") if v.strip()]
