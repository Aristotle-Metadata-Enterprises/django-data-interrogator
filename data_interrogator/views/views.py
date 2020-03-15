from django.conf import settings
from django.contrib.auth.decorators import user_passes_test
from django.core import exceptions
from django.urls import reverse
from django.db.models import functions as func
from django.http import JsonResponse, QueryDict
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import View

from django.utils.decorators import method_decorator, classonlymethod

from data_interrogator.forms import InvestigationForm
from data_interrogator.interrogators import Interrogator, allowable, normalise_field


from django import http
import json
import string

# Because of the risk of data leakage from User, Revision and Version tables,
# If a django user hasn't explicitly set up excluded models,
# we will ban interrogators from inspecting the User table
# as well as Revision and Version (which provide audit tracking and are available in django-revision)


class InterrogationMixin:
    form_class = InvestigationForm
    template_name = 'data_interrogator/table_builder.html'
    interrogator_class = Interrogator

    report_models = []
    allowed = allowable.ALL_APPS
    excluded = []

    def get_interrogator(self):
        return self.interrogator_class(self.report_models, self.allowed, self.excluded)

    def interrogate(self, *args, **kwargs):
        return self.get_interrogator().interrogate(*args, **kwargs)


class InterrogationView(View, InterrogationMixin):

    def get(self, request):
        data = {}
        form = self.form_class(interrogator=self.get_interrogator())
        has_valid_columns = any([True for c in request.GET.getlist('columns',[]) if c != ''])
        if request.method == 'GET' and has_valid_columns:
            # create a form instance and populate it with data from the request:
            form = self.form_class(request.GET, interrogator=self.get_interrogator())
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
        data['form'] = form
        return render(request, self.template_name, data)


class InterrogationAutoComplete(View, InterrogationMixin):
    def get_allowed_fields(self):
        pass

    def blank_response(self):
        return http.HttpResponse(
            json.dumps([]),
            content_type='application/json',
        )

    def get(self, request):
        interrogator = self.get_interrogator()
        # excluded_models = .excl(settings, 'DATA_INTERROGATION_DOSSIER', {}).get('excluded_models',["User","Revision","Version"])
        model_name = request.GET.get('model', "")
        q = self.request.GET.get('q', "")

        try:
            model, _ = interrogator.validate_report_model(model_name)
        except:
            return self.blank_response()

        if not model_name: # or not q:
            return self.blank_response()
        # if any("__%s"%witness.lower() in q for witness in excluded_models) or any(".%s"%witness.lower() in q for witness in excluded_models):
        #     return http.HttpResponse(
        #         json.dumps([]),
        #         content_type='application/json',
        #     )
        # model = get_base_model(*(model_name.lower().split(':')))

        # Only accept the last field in the case of trying to type a calculation. eg. end_date - start_date
        prefix = ""
        if " " in q:
            prefix,q = q.rsplit(' ',1)
            prefix = prefix+' '
        elif "(" in q:
            # ignore any command at the start
            prefix,q = q.split('(',1)
            prefix = prefix+'('
        elif "::" in q:
            # ignore any command at the start
            prefix,q = q.split('::',1)
            prefix = prefix+'::'

        args = q.split('.')
        if len(args) > 1:
            for a in args[:-1]:
                model = [f for f in model._meta.get_fields() if f.name == a][0].related_model

        fields = [f for f in model._meta.get_fields() if args[-1].lower() in f.name]

        out = []
        for f in fields:
            if interrogator.is_excluded_field(model, normalise_field(f.name) ):
                continue
            if f.related_model and interrogator.is_excluded_model(f.related_model):
                continue
            field_name = '.'.join(args[:-1]+[f.name])
            is_relation = False
            if f not in model._meta.fields:
                help_text = f.related_model.__doc__
                is_relation = True
                if not help_text:
                    help_text = "Related model - %s"%f.related_model._meta.get_verbose_name
                else:
                    help_text = help_text.lstrip('\n').split('\n')[0]
                    remove = string.whitespace.replace(' ','')
                    help_text = str(help_text).translate(remove)
                    help_text = ' '.join([c for c in help_text.split(' ') if c])
            else:
                help_text = str(f.help_text)
            if hasattr(f,'get_internal_type'):
                datatype = f.get_internal_type()
            else:
                datatype = "Many to many relationship"
            data = {
                'value': prefix+field_name,
                'lookup': args[-1],
                'name': field_name,
                'is_relation': is_relation,
                'help': help_text,
                'datatype': str(datatype),
            }
            out.append(data)

        return http.HttpResponse(
            json.dumps(out),
            content_type='application/json',
        )

class InterrogationAutocompleteUrls():
    """
    A backend for allowing new users to join the site by creating a new user
    associated with a new organization.
    """

    interrogator_view_class = InterrogationView
    interrogator_autocomplete_class = InterrogationAutoComplete

    # report_models = []
    # allowed = allowable.ALL_APPS
    # excluded = []
    def __init__(self, *args, **kwargs):
        self.report_models = kwargs.get('report_models', self.interrogator_view_class.report_models)
        self.allowed = kwargs.get('allowed', self.interrogator_view_class.allowed)
        self.excluded = kwargs.get('excluded', self.interrogator_view_class.excluded)
        self.template_name = kwargs.get('template_name', self.interrogator_view_class.template_name)
        self.path_name = kwargs.get('path_name', None)

    @property
    def urls(self):
        from django.urls import include, path
        kwargs = {
            'report_models': self.report_models,
            'allowed': self.allowed,
            'excluded': self.excluded,
        }
        print(self.interrogator_view_class)
        path_kwargs = {}
        if self.path_name:
            path_kwargs.update({'name': self.path_name})
        return [
            path('', view=self.interrogator_view_class.as_view(template_name=self.template_name, **kwargs), **path_kwargs),
            path('ac', view=self.interrogator_autocomplete_class.as_view(**kwargs)),
        ]
