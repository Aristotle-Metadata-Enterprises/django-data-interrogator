from django.conf import settings
from django.contrib.auth.decorators import user_passes_test
from django.core import exceptions
from django.core.urlresolvers import reverse
from django.db.models import F, Count, Min, Max, Sum, Value, Avg, ExpressionWrapper, DurationField, FloatField, CharField
from django.db.models import functions as func
from django.http import JsonResponse, QueryDict
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import get_template
from django.template import Context
from django.views.generic import View

import tempfile, os

from datetime import timedelta

from data_interrogator import db, forms

dossier = getattr(settings, 'DATA_INTERROGATION_DOSSIER', {})
witness_protection = dossier.get('witness_protection',["User","Revision","Version"])

from views import normalise_field, get_suspect, clean_filter

class PivotTable(View):
    form_class = forms.PivotTableForm
    template_name = 'data_interrogator/pivot.html'
    
    def get(self, request):
        data = {}
        form = self.form_class()
    
        # create a form instance and populate it with data from the request:
        form = forms.PivotTableForm(request.GET)
        # check whether it's valid:
        if form.is_valid():
            # process the data in form.cleaned_data as required
            aggregators = form.cleaned_data.get('aggregators',[])
            columns = [form.cleaned_data.get('column_1'),form.cleaned_data.get('column_2')]
            suspect = form.cleaned_data['lead_suspect']
            filters = form.cleaned_data.get('filter_by',[])

            data = pivot(suspect,columns=columns,filters=filters,aggregators=aggregators)
        data['form']=form
        return render(request, self.template_name, data)

class AdminPivotTable(PivotTable):
    form_class = forms.AdminPivotTableForm
    template_name = 'data_interrogator/admin/pivot.html'

def pivot_table(request,template='data_interrogator/pivot.html'):
    return PivotTable.as_view(template_name=template)(request)


def pivot(suspect,columns=[],filters=[],aggregators=[],headers=[],limit=None):
    columns = [normalise_field(c).lower() for c in columns
                if not (c == "" or any("__%s__"%witness in c for witness in witness_protection))
                ][:2] # only accept the first two valid columns

    errors = []
    suspect_data = {}

    count=0
    app_label,model = suspect.split(':',1)
    lead_suspect = get_suspect(app_label,model)

    for suspect in dossier.get('suspects',[]):
        if suspect['model'] == (app_label,model):
            suspect_data = suspect
            
    annotations = {}
    wrap_sheets = suspect_data.get('wrap_sheets',{})
    aliases = suspect_data.get('aliases',{})
    available_annotations = {
            "min":Min,
            "max":Max,
            "sum":Sum,
            'avg':Avg,
            "count":Count,
        }

    query_columns = []
    output_columns = []
    aggregations_columns = []
    var_name = None
    for agg,column in enumerate(aggregators):

        if column == "":
            continue # do nothings for empty fields
        if any("__%s__"%witness in column for witness in witness_protection):
            continue # do nothing for protected models

        # map names in UI to django functions
        column = normalise_field(column).lower()
        if var_name is None:
            var_name = column
        if '=' in column:
            var_name,column = column.split('=')

        if column.startswith(tuple([a+'::' for a in available_annotations.keys()])) and  " - " in column:
            # we're aggregating some mathy things, these are tricky
            split = column.split('::')
            aggs,field = split[0:-1],split[-1]
            agg = aggs[0]
            a,b = field.split(' - ')

            if a.endswith('date') and b.endswith('date'):
                expr = ExpressionWrapper(db.ForceDate(F(a))-db.ForceDate(F(b)), output_field=DurationField())
                annotations[var_name] = ExpressionWrapper(
                    available_annotations[agg](expr, distinct=True),
                    output_field=DurationField()
                )
            else:
                expr = ExpressionWrapper(F(a)-F(b), output_field=CharField())
                annotations[var_name] = available_annotations[agg](expr, distinct=True)

        elif column.startswith(tuple([a+'::' for a in available_annotations.keys()])):
            agg,field = column.split('::',1)
            annotations[var_name] = available_annotations[agg](field, distinct=True)

        else:
            pass # do nothing, this wasn't an aggregation. Just drop it.


    _filters = {}
    excludes = {}
    filters_all = {}
    expression_columns = []
    for i,expression in enumerate(filters + [v['filter'] for k,v in aliases.items() if k in columns]):
        print "-----%s-----"%expression
        key,exp,val = clean_filter(normalise_field(expression))
        key = key.strip()
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
            annotations[field] = available_annotations[agg](f, distinct=True)
            if field not in query_columns:
                query_columns.append(field)
            annotation_filters[key] = val
        elif key in annotations.keys():
            annotation_filters[key] = val
        elif key.split('__')[0] in expression_columns:
            k = key.split('__')[0]
            if 'date' in k and key.endswith('date') or 'date' in str(annotations[k]):
                #1/0
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
    filters = _filters

    out_rows = {}
    col_head = []

    try:
        rows = lead_suspect.objects
        
        rows = rows.filter(**filters)
        for key,val in filters_all.items():
            for v in val:
                rows = rows.filter(**{key:v})
        rows = rows.exclude(**excludes)
        
        columns = columns[:2]
        output_columns = columns+['cell']

        a = lead_suspect.objects.values(columns[0]).order_by().distinct()

        b = lead_suspect.objects.values(columns[1]).order_by().distinct()

        x,y = columns
        col_head,row_head = a,b

        rows = rows.values(*columns
        ).order_by().distinct().annotate(cell=Count(1)
            , **annotations
        )

        rows[0] #force a database hit to check the state of things

        from collections import OrderedDict
        default = OrderedDict([(c[x],{'count':0}) for c in col_head])
        for r in rows:
            this_row = out_rows.get(r[y],default.copy())
            this_row[r[x]] = {  'count':r['cell'],
                                'aggs':[(k,v) for k,v in r.items() if k not in ['cell',x,y]]
                            }
            out_rows[r[y]] = this_row

    except ValueError,e:
        rows = []
        errors.append("Limit must be a number greater than zero")
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
    except Exception,e:
        rows = []
        errors.append("Something when wrong - %s"%e)

    return {'rows':out_rows,'col_head':col_head,'count':count,'columns':output_columns,'errors':errors, 'suspect':suspect_data,'headers':headers }
