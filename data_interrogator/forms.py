from django import forms

from django.conf import settings
from django.template.loader import get_template
from django.template import Context

from data_interrogator.fields import MultipleCharField

suspects = getattr(settings, 'DATA_INTERROGATION_DOSSIER', {}).get('suspects',[])

SUSPECTS = []
for suspect in suspects:
    app,model = suspect['model']
    SUSPECTS.append(("%s:%s"%(app,model),model))

class InvestigationForm(forms.Form):
    lead_suspect = forms.ChoiceField(choices=SUSPECTS,required=True,label="Initial object")
    #filter_by = forms.CharField(label='Filter by', max_length=100, required=False)
    filter_by = MultipleCharField(extra=1,required=False, add_text="Add filter", remove_title="Remove filter", remove_text="-")
    columns = MultipleCharField(extra=2,required=False, add_text="Add column", remove_title="Remove column", remove_text="-")
    sort_by = MultipleCharField(extra=1,required=False, add_text="Add ordering", remove_title="Remove ordering", remove_text="-")
    #sort_by = forms.CharField(label='Sort by', max_length=100, required=False)
