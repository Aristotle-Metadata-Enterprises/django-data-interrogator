from django.conf import settings
from django.core import exceptions
from django.db.models import F, Count, Min, Max, Sum, Value, Avg, ExpressionWrapper, DurationField, FloatField, CharField
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import View

from datetime import timedelta

from data_interrogator import db, forms
from data_interrogator.interrogators import PivotInterrogator


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
            base_model = form.cleaned_data['lead_base_model']
            filters = form.cleaned_data.get('filter_by',[])

            data = PivotInterrogator(base_model=base_model,columns=columns,filters=filters,aggregators=aggregators).pivot()
        data['form']=form
        return render(request, self.template_name, data)


class AdminPivotTable(PivotTable):
    form_class = forms.AdminPivotTableForm
    template_name = 'data_interrogator/admin/pivot.html'


def pivot_table(request,template='data_interrogator/pivot.html'):
    return PivotTable.as_view(template_name=template)(request)

