from django import forms


class CSVMultipleCharField(forms.CharField):
    """
    CSV field with configurable delimiter.
    Pipe delimiter is default for historical reasons, as previously it was the only delimiter possible.
    """
    widget = forms.Textarea
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if delimiter := kwargs['delimiter']:
            self.delimiter = delimiter
        else:
            self.delimiter = "|"

        self.widget.attrs = {'class': 'multicharfields'}

    def compress(self, values):
        if values:
            values = [v for v in values if v != ""]
            return '|'.join(values)
        return ''

    def clean(self, value):
        if not value:
            value = ""
        return [val for v in value.split(self.delimiter) if (val := v.strip())]
