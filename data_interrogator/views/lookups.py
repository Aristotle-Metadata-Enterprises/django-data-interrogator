from django import http
from django.template import Template
from django.template.loader import get_template
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
from django.views.generic import View
import json
import string
from .utils import get_suspect

class FieldLookupTypeahead(View):

    def get(self, request):
        from django.conf import settings
        witness_protection = getattr(settings, 'DATA_INTERROGATION_DOSSIER', {}).get('witness_protection',["User","Revision","Version"])
        model_name = self.request.GET.get('model', None)
        q = self.request.GET.get('q', None)

        if not model_name or not q:
            return http.HttpResponse(
                json.dumps([]),
                content_type='application/json',
            )
        if any("__%s"%witness.lower() in q for witness in witness_protection) or any(".%s"%witness.lower() in q for witness in witness_protection):
            return http.HttpResponse(
                json.dumps([]),
                content_type='application/json',
            )
        model = get_suspect(*(model_name.lower().split(':')))

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
                model = [f for f in model._meta.get_fields() if f.name==a][0].related_model

        fields = [f for f in model._meta.get_fields() if args[-1].lower() in f.name]

        out = []
        for f in fields:
            if any(witness.lower() == f.name for witness in witness_protection):
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
                    help_text = str(help_text).translate(None,remove)
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
