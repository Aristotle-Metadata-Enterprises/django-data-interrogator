from django.conf import settings
from django.contrib.auth.decorators import user_passes_test
from django.core import exceptions
from django.urls import reverse
from django.db.models import F, Count, Min, Max, Sum, Value, Avg, ExpressionWrapper, DurationField, FloatField, CharField
from django.db.models import functions as func
from django.http import JsonResponse, QueryDict
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import View

from django.utils.decorators import method_decorator

from datetime import timedelta

from data_interrogator.forms import AdminInvestigationForm, InvestigationForm
from data_interrogator.db import GroupConcat, DateDiff, ForceDate, SumIf

from .utils import normalise_field, get_base_model, clean_filter

class Interrogator():
    available_annotations = {
            "min":Min,
            "max":Max,
            "sum":Sum,
            'avg':Avg,
            "count":Count,
            "substr":func.Substr,
            "group":GroupConcat,
            "concat":func.Concat,
            "sumif":SumIf,
        }
    math_infix_symbols = ['-','+','/','*']
    errors = []

    def __init__(self,base_model,columns=[],filters=[],order_by=[],headers=[],limit=None):
        self.columns = columns
        self.filters = filters
        self.order_by = order_by
        self.headers = headers
        self.limit = limit
        self.base_model_string = base_model
        self.base_model = self.get_model(base_model)

    def get_model(self,base_model):
        app_label,model = base_model.split(':',1)
        from django.contrib.contenttypes.models import ContentType
        return ContentType.objects.get(app_label=app_label.lower(),model=model.lower()).model_class()

    def get_model_queryset(self):
        return self.base_model.objects.all()

    def process_annotation_concat(self,column):
        pass

    def process_annotation(self,column):
        pass

    def verify_column(self, column):
        model = self.base_model
        args = column.split('__')
        for a in args:
            model = [f for f in model._meta.get_fields() if f.name==a][0].related_model

    def normalise_math(self,expression):
        a,b = expression.split(' - ')
        if a.endswith('date') and b.endswith('date'):
            expr = ExpressionWrapper(
                DateDiff(
                    ForceDate(F(a)),
                    ForceDate(F(b))
                ), output_field=DurationField()
            )
        else:
            expr = ExpressionWrapper(F(a)-F(b), output_field=CharField())
        return expr

    def get_field_by_name(self, model,field_name):
        from django import VERSION
        if VERSION < (1,10):
            return model._meta.get_field_by_name(field_name)[0]
        else:
            return model._meta.get_field(field_name)

    def has_forbidden_join(self, column):
        checking_model = self.base_model
        forbidden = False
        joins = column.split('__')
        for i, relation in enumerate(joins):
            if checking_model:
                try:
                    attr = self.get_field_by_name(checking_model, relation)
                    if attr.related_model:
                        if attr.related_model._meta.model_name.lower() in [w.lower() for w in excluded_models]:
                            # Despite the join/field being named differently, this column is forbidden!
                            return True
                    checking_model = attr.related_model
                except exceptions.FieldDoesNotExist:
                    pass
        return forbidden

    def interrogate(self, **kwargs):
        columns = kwargs.get('columns', self.columns)
        filters = kwargs.get('filters', self.filters)
        order_by = kwargs.get('order_by', self.order_by)
        headers = kwargs.get('headers', self.headers)
        limit = kwargs.get('limit', self.limit)

        errors = []
        base_model_data = {}
        annotation_filters = {}
        query_columns = []
        output_columns = []
        count=0
        app_label,model = self.base_model_string.split(':',1)

        for base_model in dossier.get('base_models',[]):
            if base_model['model'] == (app_label,model):
                base_model_data = base_model
                
        annotations = {}
        wrap_sheets = base_model_data.get('wrap_sheets',{})
        aliases = base_model_data.get('aliases',{})

        expression_columns = []
        for column in columns:
            if column == "":
                continue # do nothings for empty fields
                
            var_name = None
            if ':=' in column: #assigning a variable
                var_name,column = column.split(':=',1)
            elif column in aliases.keys():
                var_name = column
                column = aliases[column]['column']
            # map names in UI to django functions
            column = normalise_field(column) #.lower()
            
            if any("__%s__"%witness.lower() in column for witness in excluded_models):
                continue # do nothing for protected models

            if self.has_forbidden_join(column):
                errors.append("Joining tables with the column [{}] is forbidden, this column is removed from the output.".format(column))
                continue

            if '::' in column:
                check_col = column.split('::',1)[-1]
                if self.has_forbidden_join(check_col):
                    errors.append("Aggregating tables using the column [{}] is forbidden, this column is removed from the output.".format(column))
                    continue

            if var_name is None:
                var_name = column
            if column.startswith(tuple([a+'::' for a in self.available_annotations.keys()])) and  " - " in column:
                # we're aggregating some mathy things, these are tricky
                split = column.split('::')
                aggs,field = split[0:-1],split[-1]
                agg = aggs[0]

                expr = self.normalise_math(field)
                annotations[var_name] = self.available_annotations[agg](expr, distinct=True)
    
                query_columns.append(var_name)
                expression_columns.append(var_name)
                
            elif any(s in column for s in self.math_infix_symbols):
                annotations[var_name] = self.normalise_math(column)
                query_columns.append(var_name)
                expression_columns.append(var_name)

            elif column.startswith(tuple([a+'::' for a in self.available_annotations.keys()])):
                agg,field = column.split('::',1)
                if agg == 'sumif':
                    field,cond = field.split(',',1)
                    field = normalise_field(field)
                    conditions = {}
                    for condition in cond.split(','):
                        condition_key,condition_val = condition.split('=',1)
                        conditions[normalise_field(condition_key)] = normalise_field(condition_val)
                    annotations[var_name] = self.available_annotations[agg](field=F(field),**conditions)
                elif agg == 'join':
                    fields = []
                    for f in field.split(','):
                        if f.startswith(('"',"'")):
                            # its a string!
                            fields.append(Value(f.strip('"').strip("'")))
                        else:
                            fields.append(f)
                    annotations[var_name] = self.available_annotations[agg](*fields)
                elif agg == "substr":
                    field,i,j = (field.split(',')+[None])[0:3]
                    annotations[var_name] = self.available_annotations[agg](field,i,j)
                else:
                    annotations[var_name] = self.available_annotations[agg](field, distinct=True)
                query_columns.append(var_name)
            else:
                if column in wrap_sheets.keys():
                    cols = wrap_sheets.get(column).get('columns',[])
                    query_columns = query_columns + cols
                else:
                    query_columns.append(var_name)
                if var_name != column:
                    annotations[var_name] = F(column)
            output_columns.append(var_name)
    
        rows = self.get_model_queryset()
    
        _filters = {}
        excludes = {}
        filters_all = {}
        for i,expression in enumerate(filters + [v['filter'] for k,v in aliases.items() if k in columns]):
            #cleaned = clean_filter(normalise_field(expression))
            field,exp,val = clean_filter(normalise_field(expression))
            if self.has_forbidden_join(field):
                errors.append("Filtering with the column [{}] is forbidden, this filter is removed from the output.".format(field))
                continue

            key = '%s%s'%(field.strip(),exp)
            val = val.strip()
            
            if val.startswith('~'):
                val = F(val[1:])
            elif key.endswith('date'): # in key:
                val = (val+'-01-01')[:10] # If we are filtering by a date, make sure its 'date-like'
            elif key.endswith('__isnull'):
                if val == 'False' or val == '0':
                    val = False
                else:
                    val = bool(val)
    
            if '::' in field:
                # we got an annotated filter
                agg,f = field.split('::',1)
                field = 'f%s%s'%(i,field)
                key = 'f%s%s'%(i,key)
                annotations[field] = self.available_annotations[agg](f, distinct=True)
                if field not in query_columns:
                    query_columns.append(field)
                annotation_filters[key] = val
            elif key in annotations.keys():
                annotation_filters[key] = val
            elif key.split('__')[0] in expression_columns:
                k = key.split('__')[0]
                if 'date' in k and key.endswith('date') or 'date' in str(annotations[k]):
                    val,period = (val.rsplit(' ',1) + ['days'])[0:2] # this line is complicated, just in case there is no period or space
                    period = period.rstrip('s') # remove plurals
                    
                    kwargs = {}
                    big_multipliers = {
                        'day':1,
                        'week':7,
                        'fortnight': 14, # really?
                        'month':30, # close enough
                        'sam':297,
                        'year': 365,
                        'decade': 10*365, # wise guy huh?
                        }
                        
                    little_multipliers = {
                        'second':1,
                        'minute':60,
                        'hour':60*60,
                        'microfortnight': 1.2, # sure why not?
                        }
                        
                    if big_multipliers.get(period,None):
                        kwargs['days'] = int(val)*big_multipliers[period]
                    elif little_multipliers.get(period,None):
                        kwargs['seconds'] = int(val)*little_multipliers[period]
                        
                    annotation_filters[key] = timedelta(**kwargs)
                        
                else:
                    annotation_filters[key] = val
    
            elif key.endswith('__all'):
                key = key.rstrip('_all')
                val = [v for v in val.split(',')]
                filters_all[key] = val
            else:
                exclude = key.endswith('!')
                if exclude:
                    key = key[:-1]
                if key.endswith('__in'):
                    val = [v for v in val.split(',')]
                if exclude:
                    excludes[key] = val
                else:
                    _filters[key] = val

        try:
            rows = rows.filter(**_filters)
            for key,val in filters_all.items():
                for v in val:
                    rows = rows.filter(**{key:v})
            rows = rows.exclude(**excludes)
    
            if annotations:
                rows = rows.annotate(**annotations)
                rows = rows.filter(**annotation_filters)
            if order_by:
                ordering = map(normalise_field,order_by)
                rows = rows.order_by(*ordering)
    
            if limit:
                lim = abs(int(limit))
                rows = rows[:lim]

            rows = rows.values(*query_columns)
    
            count = rows.count()
            rows[0] #force a database hit to check the state of things
        except ValueError as e:
            rows = []
            if limit < 1:
                errors.append("Limit must be a number greater than zero")
            else:
                errors.append("Something when wrong - %s"%e)
        except IndexError as e:
            rows = []
            errors.append("No rows returned for your query, try broadening your search.")
        except exceptions.FieldError as e:
            rows = []
            if str(e).startswith('Cannot resolve keyword'):
                field = str(e).split("'")[1]
                errors.append("The requested field '%s' was not found in the database."%field)
            else:
                errors.append("An error was found with your query:\n%s"%e)
        except Exception as e:
            rows = []
            errors.append("Something when wrong - %s"%e)
    
        return {'rows':rows,'count':count,'columns':output_columns,'errors':errors, 'base_model':base_model_data,'headers':headers }


def interrogate(base_model,columns=[],filters=[],order_by=[],headers=[],limit=None):
    return Interrogator(base_model,columns=columns,filters=filters,order_by=order_by,limit=limit).interrogate()

    
class InterrogationRoom(View):
    form_class = InvestigationForm
    template_name = 'data_interrogator/interrogation_room.html'
    interrogator = Interrogator

    def interrogate(self, *args, **kwargs):
        return self.interrogator(*args, **kwargs).interrogate()

    def get(self, request):
        data = {}
        form = self.form_class()
        has_valid_columns = any([True for c in request.GET.getlist('columns',[]) if c != ''])
        if request.method == 'GET' and has_valid_columns:
            # create a form instance and populate it with data from the request:
            form = self.form_class(request.GET)
            # check whether it's valid:
            if form.is_valid():
                # process the data in form.cleaned_data as required
                filters = form.cleaned_data.get('filter_by',[])
                order_by = form.cleaned_data.get('sort_by',[])
                columns = form.cleaned_data.get('columns',[])
                base_model = form.cleaned_data['lead_base_model']
                if hasattr(request, 'user') and request.user.is_staff and request.GET.get('action','') == 'makestatic':
                    # populate the appropriate GET variables and redirect to the admin site
                    base = reverse("admin:data_interrogator_datatable_add")
                    vals = QueryDict('', mutable=True)
                    vals.setlist('columns',columns)
                    vals.setlist('filters',filters)
                    vals.setlist('orders',order_by)
                    vals['base_model'] = base_model
                    return redirect('%s?%s'%(base,vals.urlencode()))
                else:
                    data = self.interrogate(base_model,columns=columns,filters=filters,order_by=order_by)
                    # base_models = self.get_model(base_model)
                    # data = interrogate(base_models,columns=columns,filters=filters,order_by=order_by)
        data['form']=form
        return render(request, self.template_name, data)

    def get_model_queryset(self,base_model):
        app_label,model = base_model.split(':',1)
        lead_base_model = get_base_model(app_label,model)
        return lead_base_model.all()


class AdminInterrogationRoom(InterrogationRoom):
    template_name = 'data_interrogator/admin/analytics.html'
    form_class = AdminInvestigationForm

    @method_decorator(user_passes_test(lambda u: u.is_staff))
    def get(self, request):
        return super(AdminInterrogationRoom,self).get(request)

    
def datatable(request,url):
    table = get_object_or_404(data_interrogator.models.DataTablePage, url=url)

    filters = [f.filter_definition for f in table.filters.all()]
    columns = [c.column_definition for c in table.columns.all()]
    orderby = [f.ordering for f in table.order.all()]
    base_model = table.base_model
    
    template = "data_interrogator/by_the_book.html"
    if table.template_name:
        template = table.template_name

    data = Interrogator(base_model,columns=columns,filters=filters,order_by=orderby,limit=table.limit).interrogate()
    #data = interrogate(base_model,columns=columns,filters=filters,order_by=orderby,limit=table.limit)
    data['table'] = table
    return render(request, template, data)

