import json
import string

from django import http
from django.http import QueryDict, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.generic import View

from data_interrogator.forms import InvestigationForm
from data_interrogator.interrogators import Interrogator, Allowable, normalise_field

from typing import Tuple, Union, Any


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


class InterrogationView(View, InterrogationMixin):
    """The primary interrogation view"""
    def get(self, request):
        data = {}
        form = self.form_class(interrogator=self.get_interrogator())

        has_valid_columns = any([True for c in request.GET.getlist('columns', []) if c != ''])
        if request.method == 'GET' and has_valid_columns:
            # Create a form instance and populate it with data from the request:
            form = self.form_class(request.GET, interrogator=self.get_interrogator())
            if form.is_valid():
                # Process the data in form.cleaned_data as required
                filters = form.cleaned_data.get('filter_by', [])
                order_by = form.cleaned_data.get('sort_by', [])
                columns = form.cleaned_data.get('columns', [])
                base_model = form.cleaned_data['lead_base_model']

                if hasattr(request, 'user') and request.user.is_staff and request.GET.get('action', '') == 'makestatic':
                    # Populate the appropriate GET variables and redirect to the admin site
                    base = reverse("admin:data_interrogator_datatable_add")
                    vals = QueryDict('', mutable=True)
                    vals.setlist('columns', columns)
                    vals.setlist('filters', filters)
                    vals.setlist('orders', order_by)
                    vals['base_model'] = base_model
                    return redirect('%s?%s' % (base, vals.urlencode()))
                else:
                    data = self.interrogate(base_model, columns=columns, filters=filters, order_by=order_by)

        data['form'] = form
        return render(request, self.template_name, data)


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
        query = request.GET.get('query', "")

        # If we haven't been provided a model
        if not model_name:
            return self.blank_response()

        # Or the model name is invalid
        try:
            model, _ = interrogator.validate_report_model(model_name)
        except:
            return self.blank_response()

        prefix, args = self.split_query(query)

        # Exclude the base model from the calculation
        if len(args) > 1:
            for a in args[:-1]:
                model = [field for field in model._meta.get_fields() if field.name == a][0].related_model

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
            is_relation = False
            if field not in model._meta.fields:
                is_relation = True
                help_text = self.build_related_model_help_text(field.related_model.__doc__, field)
            else:
                help_text = str(field.help_text)

            if hasattr(field, 'get_internal_type'):
                datatype = field.get_internal_type()
            else:
                datatype = "Many to many relationship"

            data = {
                'value': prefix + field_name,
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
        self.path_name = kwargs.get('path_name', None)

    @property
    def urls(self):
        from django.urls import path
        kwargs = {
            'report_models': self.report_models,
            'allowed': self.allowed,
            'excluded': self.excluded,
        }

        path_kwargs = {}
        if self.path_name:
            path_kwargs.update({'name': self.path_name})
        return [
            path('', view=self.interrogator_view_class.as_view(template_name=self.template_name, **kwargs),
                 **path_kwargs),
            path('ac', view=self.interrogator_autocomplete_class.as_view(**kwargs)),
        ]
