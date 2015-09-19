from django.contrib.contenttypes.models import ContentType
from django.shortcuts import render

from django.conf import settings
from django.core import exceptions
from django.core.urlresolvers import reverse
from django.db.models import F, Count, Min, Max, ExpressionWrapper, DurationField, FloatField, CharField
from django.http import JsonResponse, QueryDict
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import get_template
from django.template import Context
from data_interrogator import forms, models, db
from datetime import timedelta

# Because of the risk of data leakage from User, Revision and Version tables,
# If a django user hasn't explicitly set up a witness protecion program,
# we will ban interrogators from inspecting the User table
# as well as Revsion and Version (which provide audit tracking and are available in django-revision)
dossier = getattr(settings, 'DATA_INTERROGATION_DOSSIER', {})
witness_protection = dossier.get('witness_protection',["User","Revision","Version"])

from django.db.models.sql.compiler import SQLCompiler

if dossier.get("suspect_grouping",False):
    try:
        if False:
            #Django 1.8?
            # Need to fix for when there is min_max queries
            pass
            print "here"
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
                base = reverse("admin:data_interrogator_datatable_add")
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
        template = table.template_name

    data = interrogate(suspect,columns=columns,filters=filters,order_by=orderby,limit=table.limit)
    data['table'] = table
    return render(request, template, data)


def interrogate(suspect,columns=[],filters=[],order_by=[],headers=[],limit=None):
    errors = []
    suspect_data = {}
    annotation_filters = {}
    query_columns = []
    output_columns = []
    count=0
    app_label,model = suspect.split(':',1)
    lead_suspect = ContentType.objects.get(app_label=app_label.lower(),model=model.lower()).model_class()

    for suspect in dossier.get('suspects',[]):
        if suspect['model'] == (app_label,model):
            suspect_data = suspect
            
    annotations = {}
    wrap_sheets = suspect_data.get('wrap_sheets',{})
    available_annotations = {"min":Min,"max":Max,"count":Count,"concat":db.Concat}
    expression_columns = []
    for column in columns:
        column = normalise_field(column).lower()

        # map names in UI to django functions

        if column == "":
            pass # do nothings for empty fields
        elif " - " in column:
            a,b = column.split(' - ')
            var_name = column
            if '=' in a:
                var_name,a = a.split('=',1)
            
            """if '__' in a:
                a = '"parlhand_%s"."%s"'%tuple(a.split('__'))
            if '__' in b:
                b = '"parlhand_%s"."%s"'%tuple(b.split('__'))"""
            print var_name,a,b
            if a.endswith('date') and b.endswith('date'):
                annotations[var_name] = ExpressionWrapper(db.ForceDate(F(a))-db.ForceDate(F(b)), output_field=DurationField())
            else:
                annotations[var_name] = ExpressionWrapper(F(a)-F(b), output_field=CharField())
            query_columns.append(var_name)
            output_columns.append(var_name)
            expression_columns.append(var_name)
        elif any("__%s__"%witness in column for witness in witness_protection):
            pass # do nothing for protected models
        elif column.startswith(tuple([a+'___' for a in available_annotations.keys()])):
            agg,field = column.split('___',1)
            annotations[column] = available_annotations[agg](field, distinct=True)
            #if agg in available_annotations.keys():
                #annotation_filters[field]=F(column)
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

    _filters = {}
    for i,expression in enumerate(filters):
        cleaned = clean_filter(normalise_field(expression))
        if '|' in cleaned:
            field,exp = cleaned.split('|')
            key,val = (field+exp).split("=",1)
        else:
            key,val = cleaned.split("=",1)
            field = key
        key = key.strip()
        val = val.strip()

        if val.startswith('='):
            val = F(val[1:])
        if '___' in field:
            # we got an annotated filter
            agg,f = field.split('___',1)
            field = 'f%s%s'%(i,field)
            key = 'f%s%s'%(i,key)
            annotations[field] = available_annotations[agg](f, distinct=True)
            if field not in query_columns:
                query_columns.append(field)
            annotation_filters[key] = val
        elif key.split('__')[0] in expression_columns:
            print key, expression_columns
            if 'date' in annotations[key]:
                annotation_filters[key] = timedelta(days=int(val))
            else:
                annotation_filters[key] = val
            print annotation_filters
        else:
            if key.endswith('__in'):
                val = [v for v in val.split(',')]
            _filters[key] = val
    filters = _filters

    rows = rows.filter(**filters)
    if annotations:
        rows = rows.annotate(**annotations)
        rows = rows.filter(**annotation_filters)
    if order_by:
        ordering = map(normalise_field,order_by)
        rows = rows.order_by(*ordering)

    print rows.query
    try:
        if limit:
            lim = abs(int(limit))
            rows = rows[:lim]
        rows = rows.values(*query_columns)
        count = rows.count()
        rows[0] #force a database hit to check the state of things
    except ValueError,e:
        rows = []
        errors.append("Limit must be a number greater than zero")
    except IndexError,e:
        rows = []
        errors.append("No rows returned for your query, try broadening your search.")
    except exceptions.FieldError,e:
        rows = []
        if str(e).startswith('Cannot resolve keyword'):
            print e
            field = str(e).split("'")[1]
            errors.append("The requested field '%s' was not found in the database."%field)
        else:
            errors.append("An error was found with your query:\n%s"%e)
    except Exception,e:
        rows = []
        raise
        errors.append("Something when wrong - %s"%e)

    return {'rows':rows,'count':count,'columns':output_columns,'errors':errors, 'suspect':suspect_data,'headers':headers }

def normalise_field(text):
    return text.strip().replace('(','___').replace(')','').replace(".","__")

def clean_filter(text):
    maps = [('<=','lte'),('<','lt'),('<>','ne'),('>=','gte'),('>','gt')]
    for a,b in maps:
        # We add a bar cause we need to to a split to get the actual field outside of here.
        text = text.replace(a,'|__%s='%b)
    return text

def clean_sort_columns(text):
    return [normalise_field(v) for v in text.split(',')]
        