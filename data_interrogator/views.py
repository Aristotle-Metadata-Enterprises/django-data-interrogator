from django.contrib.contenttypes.models import ContentType
from django.shortcuts import render
from data_interrogator import forms

from django.conf import settings
from django.template.loader import get_template
from django.template import Context

from django.db.models import Count

# Because of the risk of data leakage from User, Revision and Version tables,
# If a django user hasn't explicitly set up a witness protecion program,
# we will ban interrogators from inspecting the User table
# as well as Revsion and Version (which provide audit tracking and are available in django-revision)
witness_protection = getattr(settings, 'DATA_INTERROGATION_DOSSIER', {}).get('witness_protection',["User","Revision","Version"])

def custom_table(request):
    # if this is a POST request we need to process the form data
    rows = []
    columns = []

    # if a GET (or any other method) we'll create a blank form
    form = forms.InvestigationForm()

    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = forms.InvestigationForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            # process the data in form.cleaned_data as required
            app_label,model = form.cleaned_data['lead_suspect'].lower().split(':',1)
            lead_suspect = ContentType.objects.get(app_label=app_label,model=model).model_class()
            
            rows = lead_suspect.objects
            
            if form.cleaned_data['sort_by']:
                rows = rows.order_by(form.cleaned_data['sort_by'])
            if form.cleaned_data['filter_by']:
                kwargs = {}
                for expression in form.cleaned_data['filter_by'].split(";"):
                    key,val = expression.split("=",1)
                    key = key.strip()
                    val = val.strip()
                    kwargs[key] = val
                rows = rows.filter(**kwargs)

            cols = [col for col in form.cleaned_data['columns'] if col != ""]

            output_columns = []
            query_columns = []
            annotations = {}
            for column in cols:
                column = column.lower().replace('.','__')
                if any("__%s__"%witness in column for witness in witness_protection):
                    pass # do nothing for protected models
                elif column.startswith("count:"):
                    field = column.split(':',1)[1]
                    annotations[column] = Count(field)
                    output_columns.append(column)
                else:
                    query_columns.append(column)
                    output_columns.append(column)
            
            print annotations
            rows = rows.values(*query_columns)
            if annotations:
                rows = rows.annotate(**annotations)
            #rows = rows.values(*output_columns)
    return render(request, 'data_interrogator/custom.html', {'form': form,'rows':rows,'columns':output_columns})
