from django.contrib.contenttypes.models import ContentType
from django.shortcuts import render
from data_interrogator import forms

from django.conf import settings
from django.core import exceptions
from django.db.models import F, Count, Min, Max, sql
from django.template.loader import get_template
from django.template import Context

# Because of the risk of data leakage from User, Revision and Version tables,
# If a django user hasn't explicitly set up a witness protecion program,
# we will ban interrogators from inspecting the User table
# as well as Revsion and Version (which provide audit tracking and are available in django-revision)
dossier = getattr(settings, 'DATA_INTERROGATION_DOSSIER', {})
witness_protection = dossier.get('witness_protection',["User","Revision","Version"])

from django.db.models.sql.compiler import SQLCompiler

if not dossier.get("suspect_grouping",False):
    try:
        #Django 1.8?
        _get_group_by = SQLCompiler.get_group_by
        
        def custom_group_by(compiler,select, order_by):
            x = _get_group_by(compiler,select,order_by)
            print x
            return x
        SQLCompiler.get_group_by = custom_group_by
    except:
        _get_grouping  = SQLCompiler.get_grouping
        def custom_get_grouping(compiler,having_group_by, ordering_group_by):
            fields,thing = _get_grouping(compiler,having_group_by, ordering_group_by)
            if having_group_by:
                fields = fields[0:1]#+[".".join(f) for f in having_group_by]
            return fields,thing
            
        SQLCompiler.get_grouping = custom_get_grouping

def custom_table(request):
    data = interrogation_room(request)
    return render(request, 'data_interrogator/custom.html', data)

def interrogation_room(request):
    rows = []
    output_columns = []
    query_columns = []
    errors=[]
    suspect_data = {}
    annotation_filters = {}

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
                elif column.startswith(("count(",'min(','max(')):
                    agg,field = column.rstrip(')').split('(',1)
                    column = "%s___%s"%(agg,field)
                    # map names in UI to django functions
                    available_annotations = {"min":Min,"max":Max,"count":Count}
                    annotations[column] = available_annotations[agg](field, distinct=True)
                    if agg in ['min','max']:
                        annotation_filters[field]=F(column)
                    query_columns.append(column)
                    output_columns.append(column)
                else:
                    if column in wrap_sheets.keys():
                        cols = wrap_sheets.get(column).get('columns',[])
                        query_columns = query_columns + cols
                    query_columns.append(column)
                    output_columns.append(column)
            
            try:
                rows = lead_suspect.objects
                if annotations:
                    rows = rows.annotate(**annotations)
                    rows = rows.filter(**annotation_filters)

                if form.cleaned_data['filter_by']:
                    filters = {}
                    for expression in form.cleaned_data['filter_by']:
                        key,val = normalise_field(expression).split("=",1)
                        key = key.strip()
                        val = val.strip()
                        if val.startswith('='):
                            val = F(val[1:])
                        
                        filters[key] = val
                    rows = rows.filter(**filters)

                if form.cleaned_data['sort_by']:
                    ordering = map(normalise_field,form.cleaned_data['sort_by'])
                    rows = rows.order_by(*ordering)

                rows.query.group_by = [('parlhand_person','full_name')]
                def set_group_by(x):
                    1/0
                    x.set_group_by()
                rows = rows.values(*query_columns)
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

    return {'form': form,'rows':rows,'columns':output_columns,'errors':errors, 'suspect':suspect_data }

def normalise_field(text):
    return text.strip().replace('(','___').replace(')','').replace(".","__")

def clean_sort_columns(text):
    return [normalise_field(v) for v in text.split(',')]
        