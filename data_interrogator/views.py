from django.contrib.contenttypes.models import ContentType
from django.shortcuts import render
from data_interrogator import forms

from django.conf import settings
from django.core import exceptions
from django.db.models import F, Count, Min, Max
from django.template.loader import get_template
from django.template import Context

# Because of the risk of data leakage from User, Revision and Version tables,
# If a django user hasn't explicitly set up a witness protecion program,
# we will ban interrogators from inspecting the User table
# as well as Revsion and Version (which provide audit tracking and are available in django-revision)
dossier = getattr(settings, 'DATA_INTERROGATION_DOSSIER', {})
witness_protection = dossier.get('witness_protection',["User","Revision","Version"])

def custom_table(request):
    data = interrogation_room(request)
    return render(request, 'data_interrogator/custom.html', data)
    
def interrogation_room(request):
    # if this is a POST request we need to process the form data
    rows = []
    output_columns = []
    query_columns = []
    errors=[]
    suspect_data = {}

    # if a GET (or any other method) we'll create a blank form
    form = forms.InvestigationForm()

    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = forms.InvestigationForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            # process the data in form.cleaned_data as required
            app_label,model = form.cleaned_data['lead_suspect'].split(':',1)
            lead_suspect = ContentType.objects.get(app_label=app_label.lower(),model=model.lower()).model_class()
            
            for suspect in dossier.get('suspects',[]):
                if suspect['model'] == (app_label,model):
                    suspect_data = suspect
                    
            annotations = {}
            wrap_sheets = suspect_data.get('wrap_sheets',{})
            for column in form.cleaned_data['columns']:
                column = column.lower().replace('.','__')
                if column == "":
                    pass # do nothings for empty fields
                elif any("__%s__"%witness in column for witness in witness_protection):
                    pass # do nothing for protected models
                elif column.startswith("count("):
                    agg,field = column.rstrip(')').split('(',1)
                    column = "%s___%s"%(agg,field)
                    annotations[column] = Count(field)
                    output_columns.append(column)
                elif column.startswith("min("):
                    agg,field = column.rstrip(')').split('(',1)
                    column = "%s___%s"%(agg,field)
                    annotations[column] = Min(field)
                    output_columns.append(column)
                else:
                    if column in wrap_sheets.keys():
                        cols = wrap_sheets.get(column).get('columns',[])
                        query_columns = query_columns + cols
                    query_columns.append(column)
                    output_columns.append(column)
            
            try:
                rows = lead_suspect.objects
                
                if form.cleaned_data['filter_by']:
                    kwargs = {}
                    for expression in form.cleaned_data['filter_by']:
                        key,val = normalise_field(expression).split("=",1)
                        key = key.strip()
                        val = val.strip()
                        if val.startswith('='):
                            val = F(val[1:])
                        
                        
                        kwargs[key] = val
                    rows = rows.filter(**kwargs)
                rows = rows.values(*query_columns)
                if annotations:
                    rows = rows.annotate(**annotations)
                if form.cleaned_data['sort_by']:
                    ordering = map(normalise_field,form.cleaned_data['sort_by'])
                    rows = rows.order_by(*ordering)
                rows[0] #force a database hit to check the state of things
            except IndexError,e:
                rows = []
                errors.append("No rows returned for your query, try broadening your search.")
            except exceptions.FieldError,e:
                rows = []
                if str(e).startswith('Cannot resolve keyword'):
                    field = str(e).split("'")[1]
                    errors.append("The requested field '%s' was not found in the database."%field)
                else:
                    errors.append("An error was found with your query:\n%s"%e)
            #rows = rows.values(*output_columns)
    return {'form': form,'rows':rows,'columns':output_columns,'errors':errors, 'suspect':suspect_data }

def normalise_field(text):
    return text.strip().replace('(','___').replace(')','').replace(".","__")

def clean_sort_columns(text):
    return [normalise_field(v) for v in text.split(',')]
        