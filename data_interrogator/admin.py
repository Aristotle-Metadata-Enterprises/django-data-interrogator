from django.contrib import admin
from django.contrib.flatpages.admin import FlatpageForm, FlatPageAdmin
from django.forms.models import BaseInlineFormSet
from django.utils.translation import ugettext_lazy as _
from data_interrogator import models, forms


class DataFilterInlineFormSet(BaseInlineFormSet):
    model = models.DataTablePageFilter
    def __init__(self, *args, **kwargs):
        if self.request.GET.get('filters', None):
            filters = self.request.GET.getlist('filters')
            self.extra = len(filters)
            data = {
                'filters-TOTAL_FORMS': self.extra,
                'filters-INITIAL_FORMS': u'0',
                'filters-MAX_NUM_FORMS': u'',
            }
            for i,c in enumerate(filters):
                data['filters-%d-filter_definition'%i] = c
            kwargs['data']=data
        super(DataFilterInlineFormSet, self).__init__(*args, **kwargs)            

class DataFilterInline(admin.TabularInline):
    model = models.DataTablePageFilter
    extra = 0
    formset = DataFilterInlineFormSet

    def get_formset(self, request, obj=None, **kwargs):
        formset = super(DataFilterInline, self).get_formset(request, obj, **kwargs)
        formset.request = request
        return formset

class DataOrderInlineFormSet(BaseInlineFormSet):
    model = models.DataTablePageOrder
    def __init__(self, *args, **kwargs):
        if self.request.GET.get('orders', None):
            orders = self.request.GET.getlist('orders')
            self.extra = len(orders)
            data = {
                'order-TOTAL_FORMS': self.extra,
                'order-INITIAL_FORMS': u'0',
                'order-MAX_NUM_FORMS': u'',
            }
            for i,c in enumerate(orders):
                data['order-%d-ordering'%i] = c
            kwargs['data']=data
        super(DataOrderInlineFormSet, self).__init__(*args, **kwargs)            

class DataOrderInline(admin.TabularInline):
    model = models.DataTablePageOrder
    extra = 0
    formset = DataOrderInlineFormSet

    def get_formset(self, request, obj=None, **kwargs):
        formset = super(DataOrderInline, self).get_formset(request, obj, **kwargs)
        formset.request = request
        return formset


class DataColumnInlineFormSet(BaseInlineFormSet):
    model = models.DataTablePageColumn
    def __init__(self, *args, **kwargs):
        if self.request.GET.get('columns', None):
            cols = self.request.GET.getlist('columns')
            self.extra = len(cols)
            data = {
                'columns-TOTAL_FORMS': self.extra,
                'columns-INITIAL_FORMS': u'0',
                'columns-MAX_NUM_FORMS': u'',
            }
            for i,c in enumerate(cols):
                data['columns-%d-header_text'%i] = c
                data['columns-%d-column_definition'%i] = c
            kwargs['data']=data
        super(DataColumnInlineFormSet, self).__init__(*args, **kwargs)            

class DataColumnInline(admin.TabularInline):
    model = models.DataTablePageColumn
    extra = 1
    formset = DataColumnInlineFormSet

    def get_formset(self, request, obj=None, **kwargs):
        formset = super(DataColumnInline, self).get_formset(request, obj, **kwargs)
        formset.request = request
        return formset


class DataTablePageAdmin(admin.ModelAdmin):
    form = forms.DataTablePageForm
    fieldsets = (
        (None, {'fields': ('title','url', 'content', 'base_model')}),
        (_('Advanced options'), {'classes': ('collapse',),
        'fields': ('status', 'registration_required', 'template_name')}),
    )     
    inlines = [DataColumnInline,DataFilterInline,DataOrderInline]
    prepopulated_fields = {"url": ("title",)}

    list_display = ('url', 'title', 'status')
    list_filter = ('columns', 'status', 'registration_required')
    search_fields = ('url', 'title')

admin.site.register(models.DataTablePage, DataTablePageAdmin)
