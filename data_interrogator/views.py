from django.contrib.contenttypes.models import ContentType
from django.shortcuts import render
from data_interrogator import forms, models

from django.conf import settings
from django.core import exceptions
from django.core.urlresolvers import reverse
from django.db.models import F, Count, Min, Max, sql
from django.http import JsonResponse, QueryDict
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import get_template
from django.template import Context

# Because of the risk of data leakage from User, Revision and Version tables,
# If a django user hasn't explicitly set up a witness protecion program,
# we will ban interrogators from inspecting the User table
# as well as Revsion and Version (which provide audit tracking and are available in django-revision)
dossier = getattr(settings, 'DATA_INTERROGATION_DOSSIER', {})
witness_protection = dossier.get('witness_protection',["User","Revision","Version"])

from django.db.models.sql.compiler import SQLCompiler

if dossier.get("suspect_grouping",False):
    try:
        #Django 1.8?
        _get_group_by = SQLCompiler.get_group_by
        
        def custom_group_by(compiler,select, order_by):
            x = _get_group_by(compiler,select,order_by)
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
    return interrogation_room(request, 'data_interrogator/custom.html')

def column_generator(request):
    model = request.GET.get('model','')
    
    if model:
        app_label,model = model.split(':',1)
        lead_suspect = ContentType.objects.get(app_label=app_label.lower(),model=model.lower()).model_class()
        
        fields = [str(f.name) for f in lead_suspect._meta.fields]
        related_models = [f for f in lead_suspect._meta.get_all_field_names() if f not in fields]
        
    return JsonResponse({'model': model,'fields':fields,'related_models':related_models})

def interrogation_room(request,template='data_interrogator/custom.html'):
    data = {}
    form = forms.InvestigationForm()
    has_valid_columns = any([True for c in request.GET.getlist('columns',[]) if c != ''])
    if request.method == 'GET' and has_valid_columns:
        # create a form instance and populate it with data from the request:
        form = forms.InvestigationForm(request.GET)
        # check whether it's valid:
        if form.is_valid():
            # process the data in form.cleaned_data as required
            filters = form.cleaned_data.get('filter_by',[])
            order_by = form.cleaned_data.get('sort_by',[])
            columns = form.cleaned_data.get('columns',[])
            suspect = form.cleaned_data['lead_suspect']
            if request.user.is_superuser and request.GET.get('action','') == 'makestatic':
                # populate the appropriate GET variables and redirect to the admin site
                base = reverse("admin:data_interrogator_datatablepage_add")
                vals = QueryDict('', mutable=True)
                vals.setlist('columns',columns)
                vals.setlist('filters',filters)
                vals.setlist('orders',order_by)
                vals['base_model'] = suspect
                return redirect('%s?%s'%(base,vals.urlencode()))
            else:
                data = interrogate(suspect,columns=columns,filters=filters,order_by=order_by)
    data['form']=form
    return render(request, template, data)
    
def datatable(request,url):
    table = get_object_or_404(models.DataTablePage, url=url)

    filters = [f.filter_definition for f in table.filters.all()]
    columns = [c.column_definition for c in table.columns.all()]
    orderby = [f.ordering for f in table.order.all()]
    suspect = table.base_model
    
    template = "data_interrogator/by_the_book.html"
    if table.template_name:
        template
        
    data = interrogate(suspect,columns=columns,filters=filters,order_by=orderby)
    data['table'] = table
    return render(request, template, data)


def interrogate(suspect,columns=[],filters=[],order_by=[]):
    errors = []
    suspect_data = {}
    annotation_filters = {}
    query_columns = []
    output_columns = []
    
    app_label,model = suspect.split(':',1)
    lead_suspect = ContentType.objects.get(app_label=app_label.lower(),model=model.lower()).model_class()

    for suspect in dossier.get('suspects',[]):
        if suspect['model'] == (app_label,model):
            suspect_data = suspect
            
    annotations = {}
    wrap_sheets = suspect_data.get('wrap_sheets',{})
    for column in columns:
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
            else:
                query_columns.append(column)
            output_columns.append(column)
    
    rows = lead_suspect.objects
    if annotations:
        rows = rows.annotate(**annotations)
        rows = rows.filter(**annotation_filters)

    _filters = {}
    for expression in filters:
        key,val = normalise_field(expression).split("=",1)
        key = key.strip()
        val = val.strip()
        if val.startswith('='):
            val = F(val[1:])
        
        _filters[key] = val
    filters = _filters
    rows = rows.filter(**filters)

    if order_by:
        ordering = map(normalise_field,order_by)
        rows = rows.order_by(*ordering)

    try:
        rows = rows.values(*query_columns)
        count = rows.count()
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

    return {'rows':rows,'count':count,'columns':output_columns,'errors':errors, 'suspect':suspect_data }

def normalise_field(text):
    return text.strip().replace('(','___').replace(')','').replace(".","__")

def clean_sort_columns(text):
    return [normalise_field(v) for v in text.split(',')]
        