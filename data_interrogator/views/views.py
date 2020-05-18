import json
import string
from typing import Tuple, Union, Any, Callable

from django import http
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.generic import View
from django.contrib.auth.mixins import UserPassesTestMixin

from data_interrogator.forms import InvestigationForm
from data_interrogator.interrogators import Interrogator, Allowable, normalise_field
from data_interrogator.utils import get_all_base_models


class InterrogationMixin:
    """ Because of the risk of data leakage from User, Revision and Version tables,
        If a django user hasn't explicitly set up excluded models,
        we will ban interrogators from inspecting the User table
        as well as Revision and Version (which provide audit tracking and are available in django-revision)"""

    form_class = InvestigationForm
    template_name = 'data_interrogator/table_builder.html'
    interrogator_class = Interrogator

    report_models = []
    allowed = Allowable.ALL_APPS
    excluded = []

    def get_interrogator(self):
        return self.interrogator_class(self.report_models, self.allowed, self.excluded)

    def interrogate(self, *args, **kwargs):
        return self.get_interrogator().interrogate(*args, **kwargs)


class UserHasPermissionMixin(UserPassesTestMixin):
    test_func = 'is_superuser'

    def get_test_func(self) -> Callable:
        if self.test_func is None:
            self.test_func = 'is_superuser'
        if type(self.test_func) == str:
            return getattr(self, self.test_func)
        else:
            return self.test_func

    def is_superuser(self) -> bool:
        """A sensible default test_func that is superuser_only if one is not passed through during creation"""
        return self.request.user.is_superuser


class InterrogationView(UserHasPermissionMixin, View, InterrogationMixin):
    """The primary interrogation view, gets interrogation data and renders to a template"""

    def get_form(self):
        return self.form_class(interrogator=self.get_interrogator())

    def get_request_data(self):
        form_data = {}
        form = self.form_class(self.request.GET, interrogator=self.get_interrogator())

        if form.is_valid():
            # Get cleaned data
            form_data['filters'] = form.cleaned_data.get('filter_by', [])
            form_data['order_by'] = form.cleaned_data.get('sort_by', [])
            form_data['columns'] = form.cleaned_data.get('columns', [])
            form_data['base_model'] = form.cleaned_data['lead_base_model']

            # Add bound form to data
            form_data['form'] = form

        return form_data

    def render_to_response(self, data):
        # Add base models here so that the
        return render(self.request, self.template_name, data)

    def get(self, request):
        data = {}
        form = self.get_form()

        has_valid_columns = any([True for c in request.GET.getlist('columns', []) if c != ''])
        if has_valid_columns:
            # Create a form instance and populate it with data from the request:
            request_params = self.get_request_data()
            if request_params:
                #  If there was cleanable form data
                # Generate the interrogation data
                data = self.interrogate(request_params['base_model'],
                                        columns=request_params['columns'],
                                        filters=request_params['filters'],
                                        order_by=request_params['order_by'])
                if form:
                    # Update form to use the bound form
                    form = request_params['form']

        if form:
            data['form'] = form
        return self.render_to_response(data)


class BaseModelOptionsApi(UserHasPermissionMixin, InterrogationMixin, View):
    """Return a Object containing an Array of the base model options accessible"""

    def get(self, request):
        options = {'base_model_options': get_all_base_models(self.get_interrogator().report_models)}
        return JsonResponse(options)


class ApiInterrogationView(InterrogationView):
    """The interrogation view as a JSON view """

    def get_form(self):
        return None  # This is an API, there's no form

    def get_request_data(self):
        """Extract request data from query parameters in the API"""
        request_data = {'filters': self.request.GET.getlist('filter_by', []),
                        'order_by': self.request.GET.getlist('sort_by', []),
                        'columns': self.request.GET.getlist('columns', []),
                        'base_model': self.request.GET.get('lead_base_model')}

        transformed_request = {}

        for param, selection in request_data.items():
            if selection == ['']:
                transformed_request[param] = []
            else:
                if type(selection) == list:
                    transformed_request[param] = selection[0].split(',')
                else:
                    transformed_request[param] = selection

        return transformed_request

    def render_to_response(self, data):
        return JsonResponse(data)


class InterrogationAutoComplete(View, InterrogationMixin):
    """Build list of interrogation suggestions"""

    def get_allowed_fields(self) -> None:
        """Override allowed fields because permission checking on them is performed separately"""
        pass

    def blank_response(self) -> HttpResponse:
        """Return an empty response"""
        return HttpResponse(
            json.dumps([]),
            content_type='application/json',
        )

    def split_query(self, query) -> Tuple[Union[str, Any], Any]:
        """Split a query-string into a list of query strings that can be evaluated individually"""

        # Only accept the last field in the case of trying to type a calculation. eg. end_date - start_date
        prefix = ""
        if " " in query:
            prefix, query = query.rsplit(' ', 1)
            prefix = prefix + ' '
        elif "(" in query:
            # ignore any command at the start
            prefix, query = query.split('(', 1)
            prefix = prefix + '('
        elif "::" in query:
            # ignore any command at the start
            prefix, query = query.split('::', 1)
            prefix = prefix + '::'

        return prefix, query.split('.')

    def build_related_model_help_text(self, text, field) -> str:
        """Generate help text for the fields from a related model"""
        if not text:
            help_text = f"Related model - {field.related_model._meta.get_verbose_name}"
        else:
            help_text = text.lstrip('\n').split('\n')[0]
            remove = string.whitespace.replace(' ', '')
            help_text = str(help_text).translate(remove)
            help_text = ' '.join([c for c in help_text.split(' ') if c])

        return help_text

    def get(self, request):
        interrogator = self.get_interrogator()
        model_name = request.GET.get('model', "")
        query = request.GET.get('q', "")

        # If we haven't been provided a model
        if not model_name:
            return self.blank_response()

        try:
            model, _ = interrogator.validate_report_model(model_name)
        except:
            # Or the model name is invalid
            return self.blank_response()

        prefix, args = self.split_query(query)

        if len(args) > 1:
            # Jump across the dots to iteratively determine the 2nd to last field, which is the model
            for arg in args[:-1]:
                model = [field for field in model._meta.get_fields() if field.name == arg][0].related_model

        fields = [f for f in model._meta.get_fields() if args[-1].lower() in f.name]

        # Build list of allowed suggestions
        suggestions = []
        for field in fields:
            excluded_field = interrogator.is_excluded_field(model, normalise_field(field.name))
            excluded_model = field.related_model and interrogator.is_excluded_model(field.related_model)
            if excluded_field or excluded_model:
                # If it's an excluded field or an excluded model, don't include it as suggestion
                continue

            field_name = '.'.join(args[:-1] + [field.name])

            if field.is_relation:
                help_text = self.build_related_model_help_text(field.related_model.__doc__, field)
            else:
                help_text = str(field.help_text)
            is_relation = field.is_relation

            if hasattr(field, 'get_internal_type'):
                datatype = field.get_internal_type()
            else:
                datatype = "Many to many relationship"

            data = {
                'value': prefix + field_name,
                'field_name': field.name,
                'lookup': args[-1],
                'name': field_name,
                'is_relation': is_relation,
                'help': help_text,
                'datatype': str(datatype),
            }
            suggestions.append(data)

        return http.HttpResponse(
            json.dumps(suggestions),
            content_type='application/json',
        )


class InterrogationAutocompleteUrls:
    """
    Generates:
        A list of URLs for an url configuration for:
            - The main interrogator view
            - An autocomplete url
    """

    interrogator_view_class = InterrogationView
    interrogator_autocomplete_class = InterrogationAutoComplete

    def __init__(self, *args, **kwargs):
        self.report_models = kwargs.get('report_models', self.interrogator_view_class.report_models)
        self.allowed = kwargs.get('allowed', self.interrogator_view_class.allowed)
        self.excluded = kwargs.get('excluded', self.interrogator_view_class.excluded)
        self.template_name = kwargs.get('template_name', self.interrogator_view_class.template_name)
        self.test_func = kwargs.get('test_func', None)

    @property
    def urls(self):
        from django.urls import path
        kwargs = {
            'report_models': self.report_models,
            'allowed': self.allowed,
            'excluded': self.excluded,
        }

        return [
            path('', view=self.interrogator_view_class.as_view(template_name=self.template_name,
                                                               test_func=self.test_func, **kwargs),
                 name='interrogator'),
            path('ac', view=self.interrogator_autocomplete_class.as_view(**kwargs), name='autocomplete'),
        ]


class InterrogationAPIAutocompleteUrls(InterrogationAutocompleteUrls):
    """
    Generates:
        A list of URLs for an url configuration for:
            - The main interrogator view (.. as an API)
            - An autocomplete url
    """
    interrogator_view_class = ApiInterrogationView
    interrogator_base_model_options_class = BaseModelOptionsApi

    @property
    def urls(self):
        # Add options class to API view, as it's not needed in the main view because there's a form
        # to populate these options
        from django.urls import path
        kwargs = {
            'report_models': self.report_models,
            'allowed': self.allowed,
            'excluded': self.excluded,
        }
        urls = super().urls
        urls.append(
            path('options',
                 view=self.interrogator_base_model_options_class.as_view(test_func=self.test_func, **kwargs),
                 name="options")
        )
        return urls
