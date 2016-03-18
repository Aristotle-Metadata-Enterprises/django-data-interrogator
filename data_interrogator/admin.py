from django.contrib import admin
#from django.contrib.flatpages.admin import FlatpageForm, FlatPageAdmin
from django.forms.models import BaseInlineFormSet
from django.utils.translation import ugettext_lazy as _
import models, forms
from django.conf import settings

class TabularInlineWithRequestInFormset(admin.TabularInline):
    def get_formset(self, request, obj=None, **kwargs):
        formset = super(TabularInlineWithRequestInFormset, self).get_formset(request, obj, **kwargs)
        formset.request = request
        return formset

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

class DataFilterInline(TabularInlineWithRequestInFormset):
    model = models.DataTablePageFilter
    extra = 1
    formset = DataFilterInlineFormSet

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

class DataOrderInline(TabularInlineWithRequestInFormset):
    model = models.DataTablePageOrder
    extra = 1
    formset = DataOrderInlineFormSet

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
                data['columns-%d-position'%i] = i
            kwargs['data']=data
        super(DataColumnInlineFormSet, self).__init__(*args, **kwargs)            

class DataColumnInline(TabularInlineWithRequestInFormset):
    model = models.DataTablePageColumn
    extra = 1
    formset = DataColumnInlineFormSet
    sortable_field_name = "position"

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

class DataTableAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {'fields': ('title', 'base_model','limit')}),
    )     
    inlines = [DataColumnInline,DataFilterInline,DataOrderInline]

    list_display = ('title',)
    list_filter = ('columns',)
    search_fields = ('title',)

#admin.site.register(models.DataTablePage,DataTablePageAdmin)


admin.site.register(models.DataTable,DataTableAdmin)


def export_selected_objects(modeladmin, request, queryset):
    selected = request.POST.getlist(admin.ACTION_CHECKBOX_NAME)
    ct = ContentType.objects.get_for_model(queryset.model)
    return HttpResponseRedirect("/export/?ct=%s&ids=%s" % (ct.pk, ",".join(selected)))

#admin.site.add_action(export_selected_objects)
