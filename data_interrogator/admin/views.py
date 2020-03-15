from django.conf import settings
from django.contrib.auth.decorators import user_passes_test
from django.core import exceptions
from django.urls import reverse
from django.db.models import functions as func
from django.http import JsonResponse, QueryDict
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import View

from django.utils.decorators import method_decorator

from data_interrogator.admin.forms import AdminInvestigationForm, AdminPivotTableForm
from data_interrogator.views import InterrogationView, InterrogationAutocompleteUrls, PivotTableView, InterrogationAutoComplete
from data_interrogator.interrogators import allowable


class AdminInterrogationRoom(InterrogationView):
    template_name = 'admin/analytics/analytics.html'
    form_class = AdminInvestigationForm

    report_models = allowable.ALL_MODELS
    allowed = allowable.ALL_APPS
    excluded = []

    @method_decorator(user_passes_test(lambda u: u.is_superuser))
    def get(self, request):
        return super(AdminInterrogationRoom,self).get(request)


class AdminInterrogationAutocompleteUrls(InterrogationAutocompleteUrls):
    interrogator_view_class = AdminInterrogationRoom
    interrogator_autocomplete_class = InterrogationAutoComplete


# class AdminInterrogationAutocompleteUrls:
#     interrogator_view_class = AdminInterrogationRoom
#     interrogator_autocomplete_class = InterrogationAutoComplete

#     report_models = []
#     allowed = allowable.ALL_APPS
#     excluded = []
#     def __init__(self, *args, **kwargs):
#         self.report_models = kwargs.get('report_models', self.report_models)
#         self.allowed = kwargs.get('allowed', self.allowed)
#         self.excluded = kwargs.get('excluded', self.excluded)
#         self.template_name = kwargs.get('template_name', self.interrogator_view_class.template_name)
#         self.path_name = kwargs.get('path_name', None)

#     @property
#     def urls(self):
#         from django.urls import include, path
#         kwargs = {
#             'report_models': self.report_models,
#             'allowed': self.allowed,
#             'excluded': self.excluded,
#         }
#         print(self.interrogator_view_class)
#         path_kwargs = {}
#         if self.path_name:
#             path_kwargs.update({'name': self.path_name})
#         return [
#             path('', view=self.interrogator_view_class.as_view(template_name=self.template_name, **kwargs), **path_kwargs),
#             path('/ac', view=self.interrogator_autocomplete_class.as_view(**kwargs)),
#         ]


class AdminPivotTableView(PivotTableView):
    form_class = AdminPivotTableForm
    template_name = 'admin/analytics/pivot.html'
