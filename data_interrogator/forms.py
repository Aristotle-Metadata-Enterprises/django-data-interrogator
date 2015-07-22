from django import forms

from django.conf import settings
from django.template.loader import get_template
from django.template import Context

from data_interrogator.fields import MultipleCharField

suspects = getattr(settings, 'DATA_INTERROGATION_DOSSIER', {}).get('suspects',[])

SUSPECTS = [ (("%s:%s")%(app,model),model) for app,model in suspects ]

class InvestigationForm(forms.Form):
    lead_suspect = forms.ChoiceField(choices=SUSPECTS,required=True,label="Initial object")
    filter_by = forms.CharField(label='Filter by', max_length=100, required=False)
    columns = MultipleCharField(extra=2,required=False, add_text="Add column", remove_title="Remove column", remove_text="-")
    sort_by = forms.CharField(label='Sort by', max_length=100, required=False)
